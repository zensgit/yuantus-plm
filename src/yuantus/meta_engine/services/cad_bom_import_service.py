from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from yuantus.integrations.cad_connectors import resolve_cad_sync_key
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.cad_service import normalize_cad_attributes


def _json_text(expr):
    if hasattr(expr, "as_string"):
        return expr.as_string()
    if hasattr(expr, "astext"):
        return expr.astext
    return cast(expr, String)


def _normalize_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_node_value(node: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        if key in node and node[key] is not None:
            return node[key]
        lower = key.lower()
        for k, v in node.items():
            if str(k).lower() == lower and v is not None:
                return v
    return None


def _parse_quantity(value: Any, default: float = 1.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return default


def _normalize_refdes(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(v).strip() for v in value if str(v).strip()]
        return ",".join(sorted(set(items))) if items else None
    text = str(value).strip()
    return text or None


def _normalize_bom_payload(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    root = payload.get("root")
    if isinstance(nodes, list) and isinstance(edges, list):
        return nodes, edges, root if isinstance(root, str) else None

    root_node = None
    if isinstance(root, dict):
        root_node = root
    elif isinstance(payload, dict) and "children" in payload:
        root_node = payload

    if not root_node:
        return [], [], None

    flat_nodes: List[Dict[str, Any]] = []
    flat_edges: List[Dict[str, Any]] = []

    def _resolve_node_id(node: Dict[str, Any], index: int) -> str:
        candidate = _extract_node_value(
            node, "id", "uid", "node_id", "part_number", "item_number", "number"
        )
        return str(candidate) if candidate else f"node-{index}"

    def _walk(node: Dict[str, Any], parent_id: Optional[str], counter: List[int]) -> str:
        counter[0] += 1
        node_id = _resolve_node_id(node, counter[0])
        node = dict(node)
        node["id"] = node_id
        flat_nodes.append(node)
        if parent_id:
            edge: Dict[str, Any] = {"parent": parent_id, "child": node_id}
            for key in ("quantity", "qty", "uom", "find_num", "refdes"):
                if key in node:
                    edge[key] = node.get(key)
            flat_edges.append(edge)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                _walk(child, node_id, counter)
        return node_id

    root_id = _walk(root_node, None, [0])
    return flat_nodes, flat_edges, root_id


class CadBomImportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.bom_service = BOMService(session)

    def import_bom(
        self,
        *,
        root_item_id: str,
        bom_payload: Dict[str, Any],
        user_id: Optional[int] = None,
        roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not root_item_id:
            raise ValueError("Missing root_item_id for BOM import")
        root_item = self.session.get(Item, root_item_id)
        if not root_item:
            raise ValueError(f"Root item not found: {root_item_id}")

        part_type = self.session.get(ItemType, "Part")
        if not part_type:
            raise ValueError("Part ItemType not found")

        nodes, edges, root_node_id = _normalize_bom_payload(bom_payload or {})
        if not nodes and not edges:
            return {
                "ok": True,
                "created_items": 0,
                "existing_items": 0,
                "created_lines": 0,
                "skipped_lines": 0,
                "errors": [],
                "note": "empty_bom",
            }

        prop_names = {prop.name for prop in (part_type.properties or [])}
        cad_synced = [prop for prop in (part_type.properties or []) if prop.is_cad_synced]
        root_permission = root_item.permission_id

        def _find_existing(item_number: str) -> Optional[Item]:
            if not item_number:
                return None
            existing = (
                self.session.query(Item)
                .filter(Item.item_type_id == "Part")
                .filter(_json_text(Item.properties["item_number"]) == item_number)
                .first()
            )
            if existing:
                return existing
            return (
                self.session.query(Item)
                .filter(Item.item_type_id == "Part")
                .filter(_json_text(Item.properties["drawing_no"]) == item_number)
                .first()
            )

        def _build_properties(node: Dict[str, Any]) -> Dict[str, Any]:
            attrs = normalize_cad_attributes(node)
            props: Dict[str, Any] = {}
            item_number = _normalize_text(
                _extract_node_value(
                    attrs,
                    "part_number",
                    "item_number",
                    "number",
                    "drawing_no",
                    "id",
                )
            )
            description = _normalize_text(
                _extract_node_value(attrs, "description", "name", "title")
            )
            revision = _normalize_text(_extract_node_value(attrs, "revision", "rev"))
            material = _normalize_text(_extract_node_value(attrs, "material"))
            weight = attrs.get("weight")

            if item_number and "item_number" in prop_names:
                props["item_number"] = item_number
            if description:
                if "description" in prop_names:
                    props["description"] = description
                if "name" in prop_names:
                    props.setdefault("name", description)
            if not props.get("name") and "name" in prop_names:
                props["name"] = item_number or description or "CAD Part"
            if revision and "revision" in prop_names:
                props["revision"] = revision
            if material and "material" in prop_names:
                props["material"] = material
            if weight is not None and "weight" in prop_names:
                props["weight"] = weight

            for prop in cad_synced:
                if prop.name in props:
                    continue
                cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
                value = _extract_node_value(attrs, cad_key)
                if value is not None:
                    props[prop.name] = value

            return props

        node_map: Dict[str, str] = {}
        created_items = 0
        existing_items = 0
        errors: List[str] = []

        for node in nodes:
            node_id = str(node.get("id") or node.get("uid") or node.get("node_id") or "")
            if not node_id:
                continue

            if root_node_id and node_id == root_node_id:
                node_map[node_id] = root_item_id
                continue

            props = _build_properties(node)
            item_number = _normalize_text(props.get("item_number")) if props else None
            existing = _find_existing(item_number) if item_number else None
            if existing:
                node_map[node_id] = existing.id
                existing_items += 1
                continue

            item = Item(
                id=str(uuid.uuid4()),
                item_type_id="Part",
                config_id=str(uuid.uuid4()),
                generation=1,
                is_current=True,
                state="Active",
                properties=props,
                created_by_id=user_id,
                owner_id=user_id,
                created_at=datetime.utcnow(),
                permission_id=root_permission,
            )
            self.session.add(item)
            self.session.flush()
            node_map[node_id] = item.id
            created_items += 1

        created_lines = 0
        skipped_lines = 0

        for edge in edges:
            parent_id = _extract_node_value(edge, "parent", "from", "source")
            child_id = _extract_node_value(edge, "child", "to", "target")
            if not parent_id or not child_id:
                skipped_lines += 1
                continue
            parent_item_id = node_map.get(str(parent_id), root_item_id if str(parent_id) == root_node_id else None)
            child_item_id = node_map.get(str(child_id))
            if not parent_item_id or not child_item_id:
                skipped_lines += 1
                continue

            qty = _parse_quantity(_extract_node_value(edge, "quantity", "qty", "count"), default=1.0)
            uom = _normalize_text(_extract_node_value(edge, "uom", "unit")) or "EA"
            find_num = _normalize_text(_extract_node_value(edge, "find_num", "findno", "position"))
            refdes = _normalize_refdes(_extract_node_value(edge, "refdes", "ref_des"))

            try:
                self.bom_service.add_child(
                    parent_item_id,
                    child_item_id,
                    user_id=user_id,
                    quantity=qty,
                    uom=uom,
                    find_num=find_num,
                    refdes=refdes,
                )
                created_lines += 1
            except Exception as exc:
                skipped_lines += 1
                errors.append(str(exc))

        return {
            "ok": True,
            "created_items": created_items,
            "existing_items": existing_items,
            "created_lines": created_lines,
            "skipped_lines": skipped_lines,
            "errors": errors,
        }
