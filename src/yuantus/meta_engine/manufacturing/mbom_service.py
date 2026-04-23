"""
MBOM service (EBOM -> MBOM transformation + structure management).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from yuantus.meta_engine.manufacturing.models import BOMType, MBOMLine, ManufacturingBOM, Routing
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService, _normalize_bom_uom
from yuantus.meta_engine.services.release_validation import ValidationIssue, get_release_ruleset


def _item_uom_bucket_key(item_id: Optional[Any], uom: Optional[Any]) -> Optional[str]:
    """Return the canonical transformation-rule bucket key for item + UOM."""
    if item_id is None:
        return None
    item_text = str(item_id).strip()
    if not item_text:
        return None
    return f"{item_text}::{_normalize_bom_uom(uom)}"


def _normalize_item_uom_bucket(value: Optional[Any]) -> Optional[str]:
    """Normalize a configured item/UOM bucket key."""
    if value is None:
        return None
    item_text, sep, uom_text = str(value).partition("::")
    if not sep:
        return _item_uom_bucket_key(item_text, None)
    return _item_uom_bucket_key(item_text, uom_text)


def _normalize_item_uom_bucket_set(values: Optional[Any]) -> set[str]:
    if not values:
        return set()
    buckets: set[str] = set()
    for value in values:
        bucket = _normalize_item_uom_bucket(value)
        if bucket:
            buckets.add(bucket)
    return buckets


def _normalize_item_uom_bucket_map(mapping: Optional[Any]) -> Dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    buckets: Dict[str, Any] = {}
    for key, target_id in mapping.items():
        bucket = _normalize_item_uom_bucket(key)
        if bucket:
            buckets[bucket] = target_id
    return buckets


class MBOMService:
    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

    def create_mbom_from_ebom(
        self,
        source_item_id: str,
        name: str,
        *,
        version: str = "1.0",
        plant_code: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        user_id: Optional[int] = None,
        transformation_rules: Optional[Dict[str, Any]] = None,
    ) -> ManufacturingBOM:
        ebom_structure = self.bom_service.get_bom_structure(
            source_item_id,
            levels=20,
            effective_date=effective_from,
        )

        mbom_structure = self._transform_ebom_to_mbom(
            ebom_structure,
            transformation_rules or {},
        )

        mbom = ManufacturingBOM(
            id=str(uuid.uuid4()),
            source_item_id=source_item_id,
            name=name,
            version=version,
            bom_type=BOMType.MBOM.value,
            plant_code=plant_code,
            effective_from=effective_from,
            structure=mbom_structure,
            created_by_id=user_id,
        )
        self.session.add(mbom)
        self.session.flush()

        self._create_mbom_lines(mbom.id, mbom_structure)
        return mbom

    def _transform_ebom_to_mbom(
        self,
        node: Dict[str, Any],
        rules: Dict[str, Any],
        level: int = 0,
        rel: Optional[Dict[str, Any]] = None,
        qty_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        item = node.get("item") or node
        result: Dict[str, Any] = {
            "item": item,
            "level": level,
            "children": [],
        }

        if rel:
            rel_props = rel.get("properties") or {}
            raw_qty = rel_props.get("quantity", rel_props.get("qty", 1))
            try:
                qty = float(raw_qty)
            except (TypeError, ValueError):
                qty = 1.0
            qty *= qty_multiplier
            result["quantity"] = qty
            result["unit"] = rel_props.get("unit") or rel_props.get("uom") or "EA"
            result["ebom_relationship_id"] = rel.get("id")

        exclude_items = set(rules.get("exclude_items", []))
        exclude_item_uom_buckets = _normalize_item_uom_bucket_set(
            rules.get("exclude_item_uom_buckets")
        )
        substitute_map = rules.get("substitute_items", {})
        substitute_item_uom_buckets = _normalize_item_uom_bucket_map(
            rules.get("substitute_item_uom_buckets")
        )
        collapse_phantom = rules.get("collapse_phantom", True)

        children = node.get("children") or []
        for child_entry in children:
            rel_entry = child_entry.get("relationship") or {}
            child_node = child_entry.get("child") or {}
            child_item = child_node.get("item") or child_node
            child_id = child_item.get("id")
            rel_props = rel_entry.get("properties") or {}
            child_uom_bucket = _item_uom_bucket_key(
                child_id,
                rel_props.get("unit", rel_props.get("uom")),
            )

            if child_id in exclude_items or child_uom_bucket in exclude_item_uom_buckets:
                continue

            sub_id = (
                substitute_item_uom_buckets.get(child_uom_bucket)
                if child_uom_bucket
                else None
            )
            if sub_id is None and child_id in substitute_map:
                sub_id = substitute_map[child_id]
            if sub_id is not None:
                sub_item = self.session.get(Item, sub_id)
                if sub_item:
                    child_item = sub_item.to_dict()
                    child_node = dict(child_node)
                    child_node.update(child_item)
                    child_id = sub_id

            child_props = child_item.get("properties") or child_item
            make_buy = child_props.get("make_buy", "make")

            raw_qty = rel_props.get("quantity", rel_props.get("qty", 1))
            try:
                parent_qty = float(raw_qty)
            except (TypeError, ValueError):
                parent_qty = 1.0

            if collapse_phantom and make_buy == "phantom":
                for phantom_entry in child_node.get("children") or []:
                    grand_rel = phantom_entry.get("relationship") or {}
                    grand_child = phantom_entry.get("child") or {}
                    transformed = self._transform_ebom_to_mbom(
                        grand_child,
                        rules,
                        level + 1,
                        grand_rel,
                        qty_multiplier=qty_multiplier * parent_qty,
                    )
                    result["children"].append(transformed)
                continue

            transformed = self._transform_ebom_to_mbom(
                child_node,
                rules,
                level + 1,
                rel_entry,
                qty_multiplier=qty_multiplier,
            )
            transformed["make_buy"] = make_buy

            if rules.get("apply_scrap_rates"):
                try:
                    scrap = float(child_props.get("scrap_rate", 0))
                except (TypeError, ValueError):
                    scrap = 0.0
                if scrap > 0:
                    transformed["scrap_rate"] = scrap
                    qty = float(transformed.get("quantity", 1))
                    transformed["quantity"] = qty / (1 - scrap)

            result["children"].append(transformed)

        return result

    def _create_mbom_lines(
        self,
        mbom_id: str,
        structure: Dict[str, Any],
        parent_line_id: Optional[str] = None,
        sequence_base: int = 10,
    ) -> None:
        item = structure.get("item") or {}
        item_id = item.get("id")
        if not item_id:
            return

        line = MBOMLine(
            id=str(uuid.uuid4()),
            mbom_id=mbom_id,
            parent_line_id=parent_line_id,
            item_id=item_id,
            sequence=sequence_base,
            level=int(structure.get("level", 0) or 0),
            quantity=structure.get("quantity", 1),
            unit=structure.get("unit", "EA"),
            ebom_relationship_id=structure.get("ebom_relationship_id"),
            make_buy=structure.get("make_buy", "make"),
            scrap_rate=structure.get("scrap_rate", 0),
        )
        self.session.add(line)
        self.session.flush()

        children = structure.get("children") or []
        for i, child in enumerate(children):
            self._create_mbom_lines(
                mbom_id,
                child,
                parent_line_id=line.id,
                sequence_base=(i + 1) * 10,
            )

    def get_mbom_structure(
        self,
        mbom_id: str,
        *,
        include_operations: bool = False,
    ) -> Dict[str, Any]:
        mbom = self.session.get(ManufacturingBOM, mbom_id)
        if not mbom:
            raise ValueError(f"MBOM not found: {mbom_id}")

        if mbom.structure:
            result = dict(mbom.structure)
            if include_operations:
                result = self._attach_operations(result, mbom_id)
            return result

        lines = (
            self.session.query(MBOMLine)
            .filter(MBOMLine.mbom_id == mbom_id)
            .order_by(MBOMLine.level, MBOMLine.sequence)
            .all()
        )
        return self._build_structure_from_lines(lines, include_operations)

    def _build_structure_from_lines(
        self,
        lines: List[MBOMLine],
        include_operations: bool,
    ) -> Dict[str, Any]:
        if not lines:
            return {"children": []}

        item_ids = {line.item_id for line in lines}
        items = (
            self.session.query(Item)
            .filter(Item.id.in_(item_ids))
            .all()
        )
        item_map = {item.id: item.to_dict() for item in items}

        node_map: Dict[str, Dict[str, Any]] = {}
        roots: List[Dict[str, Any]] = []

        for line in lines:
            node_map[line.id] = {
                "item": item_map.get(line.item_id, {"id": line.item_id}),
                "line_id": line.id,
                "level": line.level,
                "quantity": float(line.quantity or 1),
                "unit": line.unit or "EA",
                "children": [],
            }

        for line in lines:
            node = node_map[line.id]
            if line.parent_line_id and line.parent_line_id in node_map:
                node_map[line.parent_line_id]["children"].append(node)
            else:
                roots.append(node)

        result = roots[0] if len(roots) == 1 else {"roots": roots}
        if include_operations:
            result = self._attach_operations(result, lines[0].mbom_id)
        return result

    def _attach_operations(self, structure: Dict[str, Any], mbom_id: str) -> Dict[str, Any]:
        from yuantus.meta_engine.manufacturing.models import Operation, Routing

        routings = (
            self.session.query(Routing)
            .filter(Routing.mbom_id == mbom_id, Routing.state == "released")
            .all()
        )
        if not routings:
            return structure

        primary = next((r for r in routings if r.is_primary), routings[0])
        operations = (
            self.session.query(Operation)
            .filter(Operation.routing_id == primary.id)
            .order_by(Operation.sequence)
            .all()
        )

        structure["routing"] = {
            "id": primary.id,
            "name": primary.name,
            "operations": [
                {
                    "id": op.id,
                    "number": op.operation_number,
                    "name": op.name,
                    "type": op.operation_type,
                    "workcenter": op.workcenter_code,
                    "setup_time": op.setup_time,
                    "run_time": op.run_time,
                }
                for op in operations
            ],
        }
        return structure

    def compare_ebom_mbom(self, ebom_item_id: str, mbom_id: str) -> Dict[str, Any]:
        ebom = self.bom_service.get_bom_structure(ebom_item_id, levels=20)
        mbom_structure = self.get_mbom_structure(mbom_id)

        differences = {
            "added_in_mbom": [],
            "removed_from_ebom": [],
            "quantity_changed": [],
            "structure_changed": [],
        }

        ebom_items = self._flatten_structure(ebom)
        mbom_items = self._flatten_structure(mbom_structure)

        ebom_keys = set(ebom_items.keys())
        mbom_keys = set(mbom_items.keys())

        for bucket_key in sorted(mbom_keys - ebom_keys):
            differences["added_in_mbom"].append(mbom_items[bucket_key])
        for bucket_key in sorted(ebom_keys - mbom_keys):
            differences["removed_from_ebom"].append(ebom_items[bucket_key])
        for bucket_key in sorted(ebom_keys & mbom_keys):
            ebom_qty = ebom_items[bucket_key].get("quantity", 1)
            mbom_qty = mbom_items[bucket_key].get("quantity", 1)
            if abs(float(ebom_qty) - float(mbom_qty)) > 0.0001:
                differences["quantity_changed"].append(
                    {
                        "item_id": ebom_items[bucket_key].get("item_id"),
                        "bucket_key": bucket_key,
                        "uom": ebom_items[bucket_key].get("uom"),
                        "ebom_quantity": ebom_qty,
                        "mbom_quantity": mbom_qty,
                    }
                )
        return differences

    def _flatten_structure(
        self,
        structure: Dict[str, Any],
        result: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        if result is None:
            result = {}

        relationship = structure.get("relationship") or {}
        node = structure.get("child") or structure
        item = node.get("item") or node
        item_id = item.get("id")
        if item_id:
            rel_props = relationship.get("properties") or {}
            if not isinstance(rel_props, dict):
                rel_props = {}
            if not rel_props and isinstance(relationship, dict):
                rel_props = relationship
            raw_quantity = rel_props.get(
                "quantity",
                rel_props.get("qty", node.get("quantity", structure.get("quantity", 1))),
            )
            raw_uom = rel_props.get(
                "uom",
                rel_props.get(
                    "unit",
                    node.get("unit", node.get("uom", structure.get("unit", structure.get("uom")))),
                ),
            )
            uom = _normalize_bom_uom(raw_uom)
            bucket_key = f"{item_id}::{uom}"
            result[bucket_key] = {
                "item": item,
                "item_id": item_id,
                "bucket_key": bucket_key,
                "uom": uom,
                "quantity": raw_quantity,
                "level": node.get("level", structure.get("level", 0)),
            }

        for child in node.get("children") or structure.get("children") or []:
            self._flatten_structure(child, result)

        for child in node.get("roots") or structure.get("roots") or []:
            self._flatten_structure(child, result)

        return result

    def _has_non_empty_structure(self, mbom: ManufacturingBOM) -> bool:
        structure = mbom.structure
        if not structure:
            return False
        if not isinstance(structure, dict):
            return bool(structure)
        if structure.get("item"):
            return True
        if structure.get("roots"):
            return bool(structure.get("roots"))
        if structure.get("children"):
            return True
        return False

    def get_release_diagnostics(
        self,
        mbom_id: str,
        *,
        ruleset_id: str = "default",
    ) -> Dict[str, Any]:
        rules = get_release_ruleset("mbom_release", ruleset_id)
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []

        mbom = self.session.get(ManufacturingBOM, mbom_id)
        if not mbom:
            errors.append(
                ValidationIssue(
                    code="mbom_not_found",
                    message=f"MBOM not found: {mbom_id}",
                    rule_id="mbom.exists",
                    details={"mbom_id": mbom_id},
                )
            )
            return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}

        for rule in rules:
            if rule == "mbom.exists":
                continue
            if rule == "mbom.not_already_released":
                if (mbom.state or "").lower() == "released":
                    errors.append(
                        ValidationIssue(
                            code="mbom_already_released",
                            message="MBOM is already released",
                            rule_id=rule,
                            details={"mbom_id": mbom_id},
                        )
                    )
            elif rule == "mbom.has_non_empty_structure":
                if not self._has_non_empty_structure(mbom):
                    errors.append(
                        ValidationIssue(
                            code="mbom_empty_structure",
                            message=f"MBOM structure is empty: {mbom_id}",
                            rule_id=rule,
                            details={"mbom_id": mbom_id},
                        )
                    )
            elif rule == "mbom.has_released_routing":
                released_routing_count = (
                    self.session.query(Routing)
                    .filter(
                        Routing.mbom_id == mbom_id,
                        Routing.state == "released",
                    )
                    .count()
                )
                if released_routing_count < 1:
                    errors.append(
                        ValidationIssue(
                            code="mbom_missing_released_routing",
                            message="MBOM requires at least one released routing before release",
                            rule_id=rule,
                            details={"mbom_id": mbom_id, "released_routing_count": released_routing_count},
                        )
                    )

        return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}

    def _validate_release_mbom_or_raise(self, mbom_id: str, *, ruleset_id: str) -> ManufacturingBOM:
        rules = get_release_ruleset("mbom_release", ruleset_id)

        mbom = self.session.get(ManufacturingBOM, mbom_id)
        if not mbom:
            raise ValueError(f"MBOM not found: {mbom_id}")

        for rule in rules:
            if rule == "mbom.exists":
                continue
            if rule == "mbom.not_already_released":
                if (mbom.state or "").lower() == "released":
                    raise ValueError("MBOM is already released")
            elif rule == "mbom.has_non_empty_structure":
                if not self._has_non_empty_structure(mbom):
                    raise ValueError(f"MBOM structure is empty: {mbom_id}")
            elif rule == "mbom.has_released_routing":
                released_routing_count = (
                    self.session.query(Routing)
                    .filter(
                        Routing.mbom_id == mbom_id,
                        Routing.state == "released",
                    )
                    .count()
                )
                if released_routing_count < 1:
                    raise ValueError("MBOM requires at least one released routing before release")

        return mbom

    def release_mbom(self, mbom_id: str, ruleset_id: str = "default") -> ManufacturingBOM:
        mbom = self._validate_release_mbom_or_raise(mbom_id, ruleset_id=ruleset_id)

        mbom.state = "released"
        self.session.add(mbom)
        self.session.flush()
        return mbom

    def reopen_mbom(self, mbom_id: str) -> ManufacturingBOM:
        mbom = self.session.get(ManufacturingBOM, mbom_id)
        if not mbom:
            raise ValueError(f"MBOM not found: {mbom_id}")
        if (mbom.state or "").lower() != "released":
            raise ValueError("Only released MBOM can be reopened")
        mbom.state = "draft"
        self.session.add(mbom)
        self.session.flush()
        return mbom
