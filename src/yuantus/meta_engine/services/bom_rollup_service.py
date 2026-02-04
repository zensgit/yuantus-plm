from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.cad_service import _parse_weight
from yuantus.meta_engine.lifecycle.guard import get_lifecycle_state
from yuantus.meta_engine.models.meta_schema import ItemType


class BOMRollupService:
    """Compute rollups for BOM trees (e.g., weight)."""

    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

    def compute_weight_rollup(
        self,
        item_id: str,
        *,
        levels: int = 10,
        effective_date=None,
        lot_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        unit_position: Optional[str] = None,
        weight_key: str = "weight",
        write_back: bool = False,
        write_back_field: str = "weight_rollup",
        write_back_mode: str = "missing",
        rounding: Optional[int] = 3,
    ) -> Dict[str, Any]:
        tree = self.bom_service.get_bom_structure(
            item_id,
            levels=levels,
            effective_date=effective_date,
            lot_number=lot_number,
            serial_number=serial_number,
            unit_position=unit_position,
        )

        visited: set[str] = set()
        rollup = self._compute_node(tree, weight_key=weight_key, visited=visited)
        summary = {
            "root_id": item_id,
            "weight_key": weight_key,
            "total_weight": rollup.get("total_weight"),
            "own_weight": rollup.get("own_weight"),
            "computed_weight": rollup.get("computed_weight"),
            "missing_items": rollup.get("missing_items", []),
            "missing_count": len(rollup.get("missing_items", [])),
            "is_partial": bool(rollup.get("missing_items")),
        }

        updates: List[Dict[str, Any]] = []
        if write_back:
            updates = self._apply_write_back(
                rollup,
                field=write_back_field,
                mode=write_back_mode,
                rounding=rounding,
            )

        return {
            "summary": summary,
            "tree": rollup,
            "updates": updates,
        }

    def _compute_node(
        self,
        node: Dict[str, Any],
        *,
        weight_key: str,
        visited: set[str],
    ) -> Dict[str, Any]:
        item_id = node.get("id")
        if item_id in visited:
            return {
                "item_id": item_id,
                "cycle_detected": True,
                "own_weight": None,
                "computed_weight": None,
                "total_weight": None,
                "missing_items": [item_id],
                "children": [],
            }
        if item_id:
            visited.add(item_id)

        own_weight_raw = node.get(weight_key)
        own_weight = self._parse_weight_value(own_weight_raw)

        children_results: List[Dict[str, Any]] = []
        computed_total = 0.0
        has_children = False
        missing_items: List[str] = []

        for child_entry in node.get("children", []) or []:
            rel = child_entry.get("relationship") or {}
            rel_props = rel.get("properties") or {}
            qty_raw = rel_props.get("quantity")
            qty = self._parse_quantity(qty_raw)
            child_node = child_entry.get("child") or {}
            child_result = self._compute_node(
                child_node, weight_key=weight_key, visited=visited
            )
            has_children = True

            line_weight = None
            if child_result.get("total_weight") is not None and qty is not None:
                line_weight = child_result["total_weight"] * qty
                computed_total += line_weight
            else:
                missing_items.extend(child_result.get("missing_items", []))

            child_result["relationship_id"] = rel.get("id")
            child_result["quantity"] = qty
            child_result["line_weight"] = line_weight
            children_results.append(child_result)

        computed_weight = computed_total if has_children else None
        total_weight = own_weight if own_weight is not None else computed_weight
        if total_weight is None and item_id:
            missing_items.append(item_id)

        result = {
            "item_id": item_id,
            "item_number": node.get("item_number") or node.get("number"),
            "item_name": node.get("name"),
            "own_weight": own_weight,
            "computed_weight": computed_weight,
            "total_weight": total_weight,
            "children": children_results,
            "missing_items": sorted(set(missing_items)),
        }

        if item_id:
            visited.discard(item_id)
        return result

    def _apply_write_back(
        self,
        rollup: Dict[str, Any],
        *,
        field: str,
        mode: str,
        rounding: Optional[int],
    ) -> List[Dict[str, Any]]:
        mode = (mode or "missing").strip().lower()
        updates: List[Dict[str, Any]] = []

        def walk(node: Dict[str, Any]):
            item_id = node.get("item_id")
            if item_id:
                own_weight = node.get("own_weight")
                computed_weight = node.get("computed_weight")
                total_weight = node.get("total_weight")
                if total_weight is not None:
                    should_write = False
                    if mode == "overwrite":
                        should_write = True
                    else:
                        should_write = own_weight is None
                    if should_write:
                        item = self.session.get(Item, item_id)
                        if item:
                            item_type = self.session.get(ItemType, item.item_type_id)
                            locked_state = None
                            if item_type:
                                state = get_lifecycle_state(
                                    self.session, item, item_type
                                )
                                if state and state.version_lock:
                                    locked_state = state.name
                            if locked_state:
                                updates.append(
                                    {
                                        "item_id": item_id,
                                        "field": field,
                                        "value": total_weight,
                                        "status": "skipped_locked",
                                        "locked_state": locked_state,
                                    }
                                )
                            else:
                                props = dict(item.properties or {})
                                value = (
                                    round(total_weight, rounding)
                                    if rounding is not None
                                    else total_weight
                                )
                                props[field] = value
                                item.properties = props
                                updates.append(
                                    {
                                        "item_id": item_id,
                                        "field": field,
                                        "value": value,
                                        "status": "updated",
                                        "own_weight": own_weight,
                                        "computed_weight": computed_weight,
                                    }
                                )
                else:
                    updates.append(
                        {
                            "item_id": item_id,
                            "field": field,
                            "value": None,
                            "status": "skipped_missing",
                        }
                    )
            for child in node.get("children", []) or []:
                walk(child)

        walk(rollup)
        return updates

    @staticmethod
    def _parse_quantity(value: Any) -> Optional[float]:
        if value is None:
            return 1.0
        try:
            return float(Decimal(str(value)))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_weight_value(value: Any) -> Optional[float]:
        parsed = _parse_weight(value)
        if isinstance(parsed, (int, float, Decimal)):
            return float(parsed)
        return None
