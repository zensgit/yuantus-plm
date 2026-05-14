"""Subcontracting order API endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.subcontracting.service import SubcontractingService

subcontracting_orders_router = APIRouter(prefix="/subcontracting", tags=["Subcontracting"])


class OrderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    requested_qty: float = Field(..., gt=0)
    item_id: Optional[str] = None
    routing_id: Optional[str] = None
    source_operation_id: Optional[str] = None
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    note: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class AssignVendorRequest(BaseModel):
    vendor_id: str = Field(..., min_length=1)
    vendor_name: Optional[str] = None


class QuantityEventRequest(BaseModel):
    quantity: float = Field(..., gt=0)
    reference: Optional[str] = None
    note: Optional[str] = None


def _event_dict(event) -> dict:
    return {
        "id": event.id,
        "order_id": event.order_id,
        "event_type": event.event_type,
        "quantity": event.quantity,
        "reference": event.reference,
        "note": event.note,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@subcontracting_orders_router.post("/orders")
async def create_order(
    req: OrderCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        order = svc.create_order(
            name=req.name,
            requested_qty=req.requested_qty,
            item_id=req.item_id,
            routing_id=req.routing_id,
            source_operation_id=req.source_operation_id,
            vendor_id=req.vendor_id,
            vendor_name=req.vendor_name,
            note=req.note,
            properties=req.properties,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.get_order_read_model(order.id)


@subcontracting_orders_router.get("/orders")
async def list_orders(
    state: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    routing_id: Optional[str] = Query(None),
    source_operation_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    orders = svc.list_orders(
        state=state,
        vendor_id=vendor_id,
        routing_id=routing_id,
        source_operation_id=source_operation_id,
    )
    return {
        "total": len(orders),
        "orders": [svc.get_order_read_model(order.id) for order in orders],
    }


@subcontracting_orders_router.get("/orders/{order_id}")
async def get_order(order_id: str, db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    try:
        return svc.get_order_read_model(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@subcontracting_orders_router.post("/orders/{order_id}/assign-vendor")
async def assign_vendor(
    order_id: str,
    req: AssignVendorRequest,
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        order = svc.assign_vendor(order_id, vendor_id=req.vendor_id, vendor_name=req.vendor_name)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return svc.get_order_read_model(order.id)


@subcontracting_orders_router.post("/orders/{order_id}/issue-material")
async def issue_material(
    order_id: str,
    req: QuantityEventRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        event = svc.record_material_issue(
            order_id,
            quantity=req.quantity,
            reference=req.reference,
            note=req.note,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _event_dict(event)


@subcontracting_orders_router.post("/orders/{order_id}/record-receipt")
async def record_receipt(
    order_id: str,
    req: QuantityEventRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        event = svc.record_receipt(
            order_id,
            quantity=req.quantity,
            reference=req.reference,
            note=req.note,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _event_dict(event)


@subcontracting_orders_router.get("/orders/{order_id}/timeline")
async def get_timeline(order_id: str, db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    order = svc.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="SubcontractOrder not found")
    events = svc.get_timeline(order_id)
    return {"total": len(events), "events": [_event_dict(event) for event in events]}
