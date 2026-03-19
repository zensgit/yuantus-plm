"""Subcontracting bootstrap service."""
from __future__ import annotations

import csv
import uuid
from datetime import datetime
from io import StringIO
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

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _render_csv(rows: List[Dict[str, Any]], fieldnames: List[str]) -> str:
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in fieldnames})
        return buffer.getvalue()

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

    def get_overview(self) -> Dict[str, Any]:
        orders = self.list_orders()
        total_requested = sum(float(order.requested_qty or 0.0) for order in orders)
        total_issued = sum(float(order.issued_qty or 0.0) for order in orders)
        total_received = sum(float(order.received_qty or 0.0) for order in orders)
        by_state: Dict[str, int] = {}
        for order in orders:
            by_state[order.state] = by_state.get(order.state, 0) + 1
        return {
            "generated_at": self._utcnow_iso(),
            "orders_total": len(orders),
            "vendors_total": len({order.vendor_id for order in orders if order.vendor_id}),
            "requested_qty_total": round(total_requested, 4),
            "issued_qty_total": round(total_issued, 4),
            "received_qty_total": round(total_received, 4),
            "open_qty_total": round(max(total_requested - total_received, 0.0), 4),
            "by_state": by_state,
        }

    def get_vendor_analytics(self) -> Dict[str, Any]:
        rows: Dict[str, Dict[str, Any]] = {}
        for order in self.list_orders():
            vendor_key = order.vendor_id or "unassigned"
            current = rows.setdefault(
                vendor_key,
                {
                    "vendor_id": order.vendor_id,
                    "vendor_name": order.vendor_name,
                    "orders_total": 0,
                    "requested_qty_total": 0.0,
                    "issued_qty_total": 0.0,
                    "received_qty_total": 0.0,
                    "open_qty_total": 0.0,
                },
            )
            requested = float(order.requested_qty or 0.0)
            issued = float(order.issued_qty or 0.0)
            received = float(order.received_qty or 0.0)
            current["orders_total"] += 1
            current["requested_qty_total"] += requested
            current["issued_qty_total"] += issued
            current["received_qty_total"] += received
            current["open_qty_total"] += max(requested - received, 0.0)
        vendors = list(rows.values())
        vendors.sort(key=lambda row: ((row["vendor_id"] or ""), row["vendor_name"] or ""))
        for vendor in vendors:
            requested = vendor["requested_qty_total"]
            received = vendor["received_qty_total"]
            vendor["completion_pct"] = round((received / requested) * 100, 2) if requested > 0 else 0.0
        return {
            "generated_at": self._utcnow_iso(),
            "vendors": vendors,
        }

    def get_receipt_analytics(self) -> Dict[str, Any]:
        rows = []
        for order in self.list_orders():
            requested = float(order.requested_qty or 0.0)
            received = float(order.received_qty or 0.0)
            rows.append(
                {
                    "order_id": order.id,
                    "name": order.name,
                    "vendor_id": order.vendor_id,
                    "state": order.state,
                    "requested_qty": requested,
                    "received_qty": received,
                    "open_qty": max(requested - received, 0.0),
                    "completion_pct": round((received / requested) * 100, 2) if requested > 0 else 0.0,
                }
            )
        rows.sort(key=lambda row: row["order_id"])
        return {
            "generated_at": self._utcnow_iso(),
            "receipts": rows,
        }

    def export_overview(self, *, fmt: str = "json") -> Dict[str, Any] | str:
        payload = self.get_overview()
        if fmt == "json":
            return payload
        if fmt == "csv":
            flattened = {
                "generated_at": payload["generated_at"],
                "orders_total": payload["orders_total"],
                "vendors_total": payload["vendors_total"],
                "requested_qty_total": payload["requested_qty_total"],
                "issued_qty_total": payload["issued_qty_total"],
                "received_qty_total": payload["received_qty_total"],
                "open_qty_total": payload["open_qty_total"],
                "by_state": payload["by_state"],
            }
            return self._render_csv([flattened], list(flattened.keys()))
        raise ValueError(f"Unsupported format: {fmt}")

    def export_vendor_analytics(self, *, fmt: str = "json") -> Dict[str, Any] | str:
        payload = self.get_vendor_analytics()
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(
                payload["vendors"],
                [
                    "vendor_id",
                    "vendor_name",
                    "orders_total",
                    "requested_qty_total",
                    "issued_qty_total",
                    "received_qty_total",
                    "open_qty_total",
                    "completion_pct",
                ],
            )
        raise ValueError(f"Unsupported format: {fmt}")

    def export_receipt_analytics(self, *, fmt: str = "json") -> Dict[str, Any] | str:
        payload = self.get_receipt_analytics()
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(
                payload["receipts"],
                [
                    "order_id",
                    "name",
                    "vendor_id",
                    "state",
                    "requested_qty",
                    "received_qty",
                    "open_qty",
                    "completion_pct",
                ],
            )
        raise ValueError(f"Unsupported format: {fmt}")
