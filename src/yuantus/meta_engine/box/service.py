"""
BoxService – CRUD, state transitions, content management, and export-meta
for the PLM box / packaging domain.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.box.models import BoxContent, BoxItem, BoxState, BoxType


# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    BoxState.DRAFT.value: [BoxState.ACTIVE.value],
    BoxState.ACTIVE.value: [BoxState.ARCHIVED.value],
    BoxState.ARCHIVED.value: [],  # terminal
}


class BoxService:
    """Domain service for PLM box / packaging management."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_box(
        self,
        *,
        name: str,
        box_type: str = BoxType.BOX.value,
        description: Optional[str] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        depth: Optional[float] = None,
        dimension_unit: str = "mm",
        tare_weight: Optional[float] = None,
        max_gross_weight: Optional[float] = None,
        weight_unit: str = "kg",
        material: Optional[str] = None,
        barcode: Optional[str] = None,
        max_quantity: Optional[int] = None,
        cost: Optional[float] = None,
        product_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[int] = None,
    ) -> BoxItem:
        # Validate box_type enum
        valid_types = {t.value for t in BoxType}
        if box_type not in valid_types:
            raise ValueError(
                f"Invalid box_type '{box_type}'. Must be one of: {sorted(valid_types)}"
            )

        box = BoxItem(
            id=str(uuid.uuid4()),
            name=name,
            box_type=box_type,
            description=description,
            state=BoxState.DRAFT.value,
            width=width,
            height=height,
            depth=depth,
            dimension_unit=dimension_unit,
            tare_weight=tare_weight,
            max_gross_weight=max_gross_weight,
            weight_unit=weight_unit,
            material=material,
            barcode=barcode,
            max_quantity=max_quantity,
            cost=cost,
            product_id=product_id,
            properties=properties,
            created_by_id=created_by_id,
        )
        self.session.add(box)
        self.session.flush()
        return box

    def get_box(self, box_id: str) -> Optional[BoxItem]:
        return self.session.get(BoxItem, box_id)

    def list_boxes(
        self,
        *,
        box_type: Optional[str] = None,
        state: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> List[BoxItem]:
        q = self.session.query(BoxItem)
        if box_type is not None:
            q = q.filter(BoxItem.box_type == box_type)
        if state is not None:
            q = q.filter(BoxItem.state == state)
        if product_id is not None:
            q = q.filter(BoxItem.product_id == product_id)
        return q.order_by(BoxItem.created_at.desc()).all()

    def update_box(self, box_id: str, **fields: Any) -> Optional[BoxItem]:
        box = self.get_box(box_id)
        if box is None:
            return None
        for key, value in fields.items():
            if hasattr(box, key) and key not in ("id", "created_at", "created_by_id"):
                setattr(box, key, value)
        self.session.flush()
        return box

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def transition_state(self, box_id: str, target_state: str) -> BoxItem:
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box '{box_id}' not found")

        allowed = _ALLOWED_TRANSITIONS.get(box.state, [])
        if target_state not in allowed:
            raise ValueError(
                f"Cannot transition from '{box.state}' to '{target_state}'. "
                f"Allowed: {allowed}"
            )
        box.state = target_state
        self.session.flush()
        return box

    # ------------------------------------------------------------------
    # Content management
    # ------------------------------------------------------------------

    def add_content(
        self,
        box_id: str,
        *,
        item_id: str,
        quantity: float = 1.0,
        lot_serial: Optional[str] = None,
        note: Optional[str] = None,
    ) -> BoxContent:
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box '{box_id}' not found")

        content = BoxContent(
            id=str(uuid.uuid4()),
            box_id=box_id,
            item_id=item_id,
            quantity=quantity,
            lot_serial=lot_serial,
            note=note,
        )
        self.session.add(content)
        self.session.flush()
        return content

    def list_contents(self, box_id: str) -> List[BoxContent]:
        return (
            self.session.query(BoxContent)
            .filter(BoxContent.box_id == box_id)
            .order_by(BoxContent.created_at)
            .all()
        )

    def remove_content(self, content_id: str) -> bool:
        content = self.session.get(BoxContent, content_id)
        if content is None:
            return False
        self.session.delete(content)
        self.session.flush()
        return True

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_meta(self, box_id: str) -> Dict[str, Any]:
        """Export box attributes + contents list for downstream integration."""
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box '{box_id}' not found")

        contents = self.list_contents(box_id)
        return {
            "id": box.id,
            "name": box.name,
            "box_type": box.box_type,
            "state": box.state,
            "dimensions": {
                "width": box.width,
                "height": box.height,
                "depth": box.depth,
                "unit": box.dimension_unit,
            },
            "weight": {
                "tare": box.tare_weight,
                "max_gross": box.max_gross_weight,
                "unit": box.weight_unit,
            },
            "material": box.material,
            "barcode": box.barcode,
            "max_quantity": box.max_quantity,
            "cost": box.cost,
            "product_id": box.product_id,
            "is_active": box.is_active,
            "contents": [
                {
                    "id": c.id,
                    "item_id": c.item_id,
                    "quantity": c.quantity,
                    "lot_serial": c.lot_serial,
                    "note": c.note,
                }
                for c in contents
            ],
        }

    # ------------------------------------------------------------------
    # Analytics (C20)
    # ------------------------------------------------------------------

    def overview(self) -> Dict[str, Any]:
        """High-level overview: total counts, state and type breakdowns."""
        boxes = self.session.query(BoxItem).all()
        by_state: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        active_count = 0
        total_cost = 0.0

        for b in boxes:
            by_state[b.state] = by_state.get(b.state, 0) + 1
            by_type[b.box_type] = by_type.get(b.box_type, 0) + 1
            if b.is_active:
                active_count += 1
            if b.cost is not None:
                total_cost += b.cost

        return {
            "total": len(boxes),
            "active": active_count,
            "by_state": by_state,
            "by_type": by_type,
            "total_cost": total_cost,
        }

    def material_analytics(self) -> Dict[str, Any]:
        """Breakdown of boxes by material value."""
        boxes = self.session.query(BoxItem).all()
        by_material: Dict[str, int] = {}
        no_material = 0

        for b in boxes:
            if b.material:
                by_material[b.material] = by_material.get(b.material, 0) + 1
            else:
                no_material += 1

        return {
            "total": len(boxes),
            "by_material": by_material,
            "no_material": no_material,
        }

    def contents_summary(self, box_id: str) -> Dict[str, Any]:
        """Aggregate contents of a single box for quick overview."""
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box '{box_id}' not found")

        contents = self.list_contents(box_id)
        distinct_items: set = set()
        total_quantity = 0.0
        has_lot_serial = 0

        for c in contents:
            distinct_items.add(c.item_id)
            total_quantity += (c.quantity or 0.0)
            if c.lot_serial:
                has_lot_serial += 1

        return {
            "box_id": box.id,
            "box_name": box.name,
            "total_lines": len(contents),
            "distinct_items": len(distinct_items),
            "total_quantity": total_quantity,
            "has_lot_serial": has_lot_serial,
        }

    def export_overview(self) -> Dict[str, Any]:
        """Export-ready overview payload with overview + material analytics."""
        return {
            "overview": self.overview(),
            "material_analytics": self.material_analytics(),
        }

    def export_contents(self, box_id: str) -> Dict[str, Any]:
        """Export-ready contents payload: summary + full line list."""
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box '{box_id}' not found")

        summary = self.contents_summary(box_id)
        contents = self.list_contents(box_id)
        return {
            **summary,
            "contents": [
                {
                    "id": c.id,
                    "item_id": c.item_id,
                    "quantity": c.quantity,
                    "lot_serial": c.lot_serial,
                    "note": c.note,
                }
                for c in contents
            ],
        }

    # ------------------------------------------------------------------
    # Analytics / ops report (C23)
    # ------------------------------------------------------------------

    def transition_summary(self) -> Dict[str, Any]:
        """Aggregate state distribution across all boxes with transition eligibility counts."""
        boxes = self.session.query(BoxItem).all()
        by_state: Dict[str, int] = {}
        draft_to_active_eligible = 0
        active_to_archive_eligible = 0

        for b in boxes:
            by_state[b.state] = by_state.get(b.state, 0) + 1
            if b.state == BoxState.DRAFT.value:
                draft_to_active_eligible += 1
            elif b.state == BoxState.ACTIVE.value:
                active_to_archive_eligible += 1

        return {
            "total": len(boxes),
            "by_state": by_state,
            "draft_to_active_eligible": draft_to_active_eligible,
            "active_to_archive_eligible": active_to_archive_eligible,
        }

    def active_archive_breakdown(self) -> Dict[str, Any]:
        """Breakdown of active vs archived boxes with cost and type detail."""
        boxes = self.session.query(BoxItem).all()

        active_boxes: List[BoxItem] = []
        archived_boxes: List[BoxItem] = []

        for b in boxes:
            if b.state == BoxState.ACTIVE.value:
                active_boxes.append(b)
            elif b.state == BoxState.ARCHIVED.value:
                archived_boxes.append(b)

        def _build_group(group: List[BoxItem]) -> Dict[str, Any]:
            total_cost = 0.0
            by_type: Dict[str, int] = {}
            for b in group:
                if b.cost is not None:
                    total_cost += b.cost
                by_type[b.box_type] = by_type.get(b.box_type, 0) + 1
            return {
                "count": len(group),
                "total_cost": total_cost,
                "by_type": by_type,
            }

        return {
            "active": _build_group(active_boxes),
            "archived": _build_group(archived_boxes),
        }

    def ops_report(self, box_id: str) -> Dict[str, Any]:
        """Per-box operational report: box info + state transition eligibility + contents summary."""
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box '{box_id}' not found")

        contents = self.list_contents(box_id)
        total_quantity = 0.0
        for c in contents:
            total_quantity += (c.quantity or 0.0)

        return {
            "box_id": box.id,
            "name": box.name,
            "state": box.state,
            "box_type": box.box_type,
            "can_activate": box.state == BoxState.DRAFT.value,
            "can_archive": box.state == BoxState.ACTIVE.value,
            "is_terminal": box.state == BoxState.ARCHIVED.value,
            "contents_count": len(contents),
            "total_quantity": total_quantity,
            "material": box.material,
            "cost": box.cost,
        }

    def export_ops_report(self) -> Dict[str, Any]:
        """Export-ready payload combining transition_summary + active_archive_breakdown."""
        return {
            "transition_summary": self.transition_summary(),
            "active_archive_breakdown": self.active_archive_breakdown(),
        }

    # ------------------------------------------------------------------
    # Reconciliation / audit (C26)
    # ------------------------------------------------------------------

    def reconciliation_overview(self) -> Dict[str, Any]:
        """Fleet-wide reconciliation: completeness and consistency metrics."""
        boxes = self.session.query(BoxItem).all()

        total = len(boxes)
        with_contents = 0
        without_contents = 0
        with_barcode = 0
        without_barcode = 0
        with_dimensions = 0
        with_weight = 0

        for b in boxes:
            contents = self.list_contents(b.id)
            if contents:
                with_contents += 1
            else:
                without_contents += 1
            if b.barcode:
                with_barcode += 1
            else:
                without_barcode += 1
            if b.width is not None and b.height is not None and b.depth is not None:
                with_dimensions += 1
            if b.tare_weight is not None or b.max_gross_weight is not None:
                with_weight += 1

        completeness_pct = round(
            (with_barcode + with_dimensions + with_weight) / (total * 3) * 100, 1
        ) if total > 0 else 0.0

        return {
            "total": total,
            "with_contents": with_contents,
            "without_contents": without_contents,
            "with_barcode": with_barcode,
            "without_barcode": without_barcode,
            "with_dimensions": with_dimensions,
            "with_weight": with_weight,
            "completeness_pct": completeness_pct,
        }

    def audit_summary(self) -> Dict[str, Any]:
        """Audit checks: missing fields, data quality issues."""
        boxes = self.session.query(BoxItem).all()

        no_material: List[str] = []
        no_dimensions: List[str] = []
        no_cost: List[str] = []
        archived_with_contents: List[str] = []

        for b in boxes:
            if not b.material:
                no_material.append(b.id)
            if b.width is None or b.height is None or b.depth is None:
                no_dimensions.append(b.id)
            if b.cost is None:
                no_cost.append(b.id)
            if b.state == BoxState.ARCHIVED.value:
                contents = self.list_contents(b.id)
                if contents:
                    archived_with_contents.append(b.id)

        return {
            "total": len(boxes),
            "no_material": len(no_material),
            "no_material_ids": no_material,
            "no_dimensions": len(no_dimensions),
            "no_dimensions_ids": no_dimensions,
            "no_cost": len(no_cost),
            "no_cost_ids": no_cost,
            "archived_with_contents": len(archived_with_contents),
            "archived_with_contents_ids": archived_with_contents,
        }

    def box_reconciliation(self, box_id: str) -> Dict[str, Any]:
        """Per-box reconciliation: completeness checks and content summary."""
        box = self.get_box(box_id)
        if box is None:
            raise ValueError(f"Box '{box_id}' not found")

        contents = self.list_contents(box_id)
        total_quantity = 0.0
        for c in contents:
            total_quantity += (c.quantity or 0.0)

        has_dimensions = (
            box.width is not None
            and box.height is not None
            and box.depth is not None
        )
        has_weight = (
            box.tare_weight is not None or box.max_gross_weight is not None
        )

        checks_passed = sum([
            bool(box.material),
            has_dimensions,
            has_weight,
            bool(box.barcode),
            bool(box.cost is not None),
        ])

        return {
            "box_id": box.id,
            "name": box.name,
            "state": box.state,
            "has_material": bool(box.material),
            "has_dimensions": has_dimensions,
            "has_weight": has_weight,
            "has_barcode": bool(box.barcode),
            "has_cost": box.cost is not None,
            "checks_passed": checks_passed,
            "checks_total": 5,
            "contents_count": len(contents),
            "total_quantity": total_quantity,
        }

    def export_box_reconciliation(self) -> Dict[str, Any]:
        """Export-ready reconciliation payload: overview + audit summary."""
        return {
            "reconciliation_overview": self.reconciliation_overview(),
            "audit_summary": self.audit_summary(),
        }
