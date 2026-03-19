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
