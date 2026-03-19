"""Subcontracting bootstrap service."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.manufacturing.models import Operation
from yuantus.meta_engine.subcontracting.models import (
    SubcontractEventType,
    SubcontractOrder,
    SubcontractOrderEvent,
    SubcontractOrderState,
)


class SubcontractingService:
    def __init__(self, session: Session):
        self.session = session

    def create_order(
        self,
        *,
        name: str,
        requested_qty: float,
        item_id: Optional[str] = None,
        routing_id: Optional[str] = None,
        source_operation_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        vendor_name: Optional[str] = None,
        note: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> SubcontractOrder:
        if requested_qty <= 0:
            raise ValueError("requested_qty must be > 0")
        operation = self._get_operation(source_operation_id) if source_operation_id else None
        order = SubcontractOrder(
            id=str(uuid.uuid4()),
            name=name,
            item_id=item_id,
            routing_id=routing_id or getattr(operation, "routing_id", None),
            source_operation_id=source_operation_id,
            vendor_id=vendor_id or getattr(operation, "subcontractor_id", None),
            vendor_name=vendor_name,
            state=SubcontractOrderState.DRAFT.value,
            requested_qty=requested_qty,
            note=note,
            properties=properties or {},
            created_by_id=user_id,
        )
        self.session.add(order)
        self.session.flush()
        return order

    def list_orders(
        self,
        *,
        state: Optional[str] = None,
        vendor_id: Optional[str] = None,
        routing_id: Optional[str] = None,
        source_operation_id: Optional[str] = None,
    ) -> List[SubcontractOrder]:
        orders = self.session.query(SubcontractOrder).order_by(
            SubcontractOrder.created_at.desc()
        ).all()
        if state is not None:
            orders = [order for order in orders if order.state == state]
        if vendor_id is not None:
            orders = [order for order in orders if order.vendor_id == vendor_id]
        if routing_id is not None:
            orders = [order for order in orders if order.routing_id == routing_id]
        if source_operation_id is not None:
            orders = [
                order
                for order in orders
                if order.source_operation_id == source_operation_id
            ]
        return orders

    def get_order(self, order_id: str) -> Optional[SubcontractOrder]:
        return self.session.get(SubcontractOrder, order_id)

    def assign_vendor(
        self,
        order_id: str,
        *,
        vendor_id: str,
        vendor_name: Optional[str] = None,
    ) -> SubcontractOrder:
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        order.vendor_id = vendor_id
        if vendor_name is not None:
            order.vendor_name = vendor_name
        self.session.flush()
        return order

    def record_material_issue(
        self,
        order_id: str,
        *,
        quantity: float,
        reference: Optional[str] = None,
        note: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> SubcontractOrderEvent:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        order.issued_qty = float(order.issued_qty or 0.0) + quantity
        if order.issued_qty > 0:
            order.state = SubcontractOrderState.ISSUED.value
        event = self._create_event(
            order_id=order_id,
            event_type=SubcontractEventType.MATERIAL_ISSUE.value,
            quantity=quantity,
            reference=reference,
            note=note,
            user_id=user_id,
        )
        self.session.flush()
        return event

    def record_receipt(
        self,
        order_id: str,
        *,
        quantity: float,
        reference: Optional[str] = None,
        note: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> SubcontractOrderEvent:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        order.received_qty = float(order.received_qty or 0.0) + quantity
        if order.received_qty >= float(order.requested_qty or 0.0):
            order.state = SubcontractOrderState.COMPLETED.value
        else:
            order.state = SubcontractOrderState.PARTIALLY_RECEIVED.value
        event = self._create_event(
            order_id=order_id,
            event_type=SubcontractEventType.RECEIPT.value,
            quantity=quantity,
            reference=reference,
            note=note,
            user_id=user_id,
        )
        self.session.flush()
        return event

    def get_timeline(self, order_id: str) -> List[SubcontractOrderEvent]:
        events = self.session.query(SubcontractOrderEvent).order_by(
            SubcontractOrderEvent.created_at.asc()
        )
        return [event for event in events.all() if event.order_id == order_id]

    def get_order_read_model(self, order_id: str) -> Dict[str, Any]:
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        operation = self._get_operation(order.source_operation_id) if order.source_operation_id else None
        timeline = self.get_timeline(order.id)
        requested_qty = float(order.requested_qty or 0.0)
        received_qty = float(order.received_qty or 0.0)
        completion_pct = round((received_qty / requested_qty) * 100, 2) if requested_qty > 0 else 0.0
        return {
            "id": order.id,
            "name": order.name,
            "item_id": order.item_id,
            "routing_id": order.routing_id,
            "source_operation_id": order.source_operation_id,
            "state": order.state,
            "vendor_id": order.vendor_id,
            "vendor_name": order.vendor_name,
            "requested_qty": requested_qty,
            "issued_qty": float(order.issued_qty or 0.0),
            "received_qty": received_qty,
            "open_qty": max(requested_qty - received_qty, 0.0),
            "completion_pct": completion_pct,
            "timeline_total": len(timeline),
            "operation": {
                "operation_id": getattr(operation, "id", None),
                "routing_id": getattr(operation, "routing_id", None),
                "operation_number": getattr(operation, "operation_number", None),
                "name": getattr(operation, "name", None),
                "is_subcontracted": bool(getattr(operation, "is_subcontracted", False)) if operation else False,
                "subcontractor_id": getattr(operation, "subcontractor_id", None),
            },
        }

    def _create_event(
        self,
        *,
        order_id: str,
        event_type: str,
        quantity: float,
        reference: Optional[str],
        note: Optional[str],
        user_id: Optional[int],
    ) -> SubcontractOrderEvent:
        event = SubcontractOrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type=event_type,
            quantity=quantity,
            reference=reference,
            note=note,
            created_by_id=user_id,
            properties={},
        )
        self.session.add(event)
        return event

    def _get_operation(self, operation_id: Optional[str]) -> Optional[Operation]:
        if not operation_id:
            return None
        return self.session.get(Operation, operation_id)
