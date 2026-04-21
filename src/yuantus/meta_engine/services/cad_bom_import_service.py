from __future__ import annotations

import re
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


_NATURAL_SORT_RE = re.compile(r"(\d+)")


def _json_text(expr):
    if hasattr(expr, "as_string"):
        return expr.as_string()
    if hasattr(expr, "astext"):
        return expr.astext
    return cast(expr, String)


def _normalize_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        return None
    text = str(value).strip()
    return text or None


def _normalize_localized_text_map(value: Any) -> Optional[Dict[str, str]]:
    if not isinstance(value, dict):
        return None
    result: Dict[str, str] = {}
    for raw_lang, raw_text in value.items():
        lang = str(raw_lang).strip()
        text = _normalize_text(raw_text)
        if lang and text:
            result[lang] = text
    return result or None


def _extract_node_value(node: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        if key in node and node[key] is not None:
            return node[key]
        lower = key.lower()
        for k, v in node.items():
            if str(k).lower() == lower and v is not None:
                return v
    return None


def _extract_localized_text_map(
    node: Dict[str, Any],
    field_name: str,
    *,
    direct_keys: Tuple[str, ...] = (),
) -> Optional[Dict[str, str]]:
    keys = direct_keys or (field_name,)
    for key in keys:
        localized = _normalize_localized_text_map(_extract_node_value(node, key))
        if localized:
            return localized

    for suffix in ("i18n", "translations"):
        localized = _normalize_localized_text_map(
            _extract_node_value(node, f"{field_name}_{suffix}")
        )
        if localized:
            return localized

    for bucket_name in ("i18n", "translations"):
        bucket = _extract_node_value(node, bucket_name)
        if isinstance(bucket, dict):
            localized = _normalize_localized_text_map(
                _extract_node_value(bucket, field_name)
            )
            if localized:
                return localized

    return None


def _localized_scalar_fallback(
    localized: Optional[Dict[str, str]],
    *,
    preferred_langs: Tuple[str, ...] = ("en_US", "en", "zh_CN", "zh"),
) -> Optional[str]:
    if not localized:
        return None
    for lang in preferred_langs:
        value = localized.get(lang)
        if value:
            return value
    return next(iter(localized.values()), None)


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


def _normalize_uom(value: Optional[Any], *, default: str = "EA") -> str:
    text = _normalize_text(value)
    return (text or default).upper()


def _refdes_tokens(value: Any) -> List[str]:
    """Extract individual refdes tokens from a payload value.

    Accepts list/tuple/set of values, or a comma-separated string. Returns
    stripped, non-empty tokens preserving input order (dedup and sort happen
    at emit time so aggregation can accumulate tokens across duplicate edges).
    None entries and blank strings are filtered out.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [
            str(v).strip()
            for v in value
            if v is not None and str(v).strip()
        ]
    text = str(value).strip()
    if not text:
        return []
    return [token.strip() for token in text.split(",") if token.strip()]


def _natural_refdes_sort_key(token: str) -> Tuple[Tuple[Any, ...], ...]:
    """Sort reference designators by text prefix and numeric chunks.

    This keeps deterministic grouping by designator prefix while ordering
    R2 before R10, C2 before C10, etc. The original token is retained as a
    final tie-breaker so case variants remain stable without normalizing data.
    """
    parts: List[Tuple[Any, ...]] = []
    for part in _NATURAL_SORT_RE.split(str(token)):
        if not part:
            continue
        if part.isdigit():
            parts.append((1, int(part)))
        else:
            parts.append((0, part.casefold(), part))
    return tuple(parts)


def _join_refdes_tokens(tokens: Any) -> Optional[str]:
    """Deduplicate + natural-sort + comma-join a token collection.

    None entries and blank strings are filtered out before dedup.
    """
    unique_sorted = sorted(
        {
            str(t).strip()
            for t in (tokens or [])
            if t is not None and str(t).strip()
        },
        key=_natural_refdes_sort_key,
    )
    return ",".join(unique_sorted) if unique_sorted else None


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
            description_i18n = _extract_localized_text_map(
                attrs,
                "description",
                direct_keys=("description",),
            )
            if not description_i18n:
                description_i18n = _extract_localized_text_map(
                    attrs,
                    "title",
                    direct_keys=("title",),
                )
            name_i18n = _extract_localized_text_map(
                attrs,
                "name",
                direct_keys=("name", "title"),
            )
            revision = _normalize_text(_extract_node_value(attrs, "revision", "rev"))
            material = _normalize_text(_extract_node_value(attrs, "material"))
            weight = attrs.get("weight")

            if item_number and "item_number" in prop_names:
                props["item_number"] = item_number
            if name_i18n and "name" in prop_names:
                props["name_i18n"] = name_i18n
            if description_i18n and "description" in prop_names:
                props["description_i18n"] = description_i18n
            if description:
                if "description" in prop_names:
                    props["description"] = description
                if "name" in prop_names:
                    props.setdefault("name", description)
            elif description_i18n and "description" in prop_names:
                props["description"] = _localized_scalar_fallback(description_i18n)
            if name_i18n and "name" in prop_names:
                props.setdefault("name", _localized_scalar_fallback(name_i18n))
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

        # Phase 1: resolve + aggregate duplicate edges by (parent, child, normalized_uom).
        # Duplicates sum qty; find_num keeps first non-empty; refdes tokens accumulate
        # across edges and are dedup/sorted at emit time.
        created_lines = 0
        skipped_lines = 0
        aggregated: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        aggregation_order: List[Tuple[str, str, str]] = []

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
            uom = _normalize_uom(_extract_node_value(edge, "uom", "unit"))
            find_num = _normalize_text(_extract_node_value(edge, "find_num", "findno", "position"))
            refdes_tokens = _refdes_tokens(_extract_node_value(edge, "refdes", "ref_des"))

            key = (parent_item_id, child_item_id, uom)
            existing_agg = aggregated.get(key)
            if existing_agg is None:
                aggregated[key] = {
                    "parent_item_id": parent_item_id,
                    "child_item_id": child_item_id,
                    "uom": uom,
                    "quantity": qty,
                    "find_num": find_num,
                    "refdes_tokens": set(refdes_tokens),
                    "merged_count": 1,
                }
                aggregation_order.append(key)
            else:
                existing_agg["quantity"] += qty
                if not existing_agg.get("find_num") and find_num:
                    existing_agg["find_num"] = find_num
                existing_agg["refdes_tokens"].update(refdes_tokens)
                existing_agg["merged_count"] += 1

        dedup_aggregated = sum(
            agg["merged_count"] - 1 for agg in aggregated.values()
        )

        # Phase 2: emit one add_child per aggregated key, preserving first-seen order.
        for key in aggregation_order:
            agg = aggregated[key]
            refdes_str = _join_refdes_tokens(agg["refdes_tokens"])
            try:
                self.bom_service.add_child(
                    agg["parent_item_id"],
                    agg["child_item_id"],
                    user_id=user_id,
                    quantity=agg["quantity"],
                    uom=agg["uom"],
                    find_num=agg.get("find_num"),
                    refdes=refdes_str,
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
            "dedup_aggregated": dedup_aggregated,
            "errors": errors,
        }
