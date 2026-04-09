"""Subcontracting bootstrap API endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.subcontracting.service import SubcontractingService

subcontracting_router = APIRouter(prefix="/subcontracting", tags=["Subcontracting"])


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


class ApprovalRoleMappingRequest(BaseModel):
    role_code: str = Field(..., min_length=1, max_length=100)
    scope_type: str = Field(..., min_length=1, max_length=30)
    scope_value: Optional[str] = None
    scope_vendor_id: Optional[str] = None
    scope_policy_code: Optional[str] = None
    owner: Optional[str] = None
    team: Optional[str] = None
    required: bool = False
    sequence: int = Field(10, gt=0)
    fallback_role: Optional[str] = None
    active: bool = True
    properties: Optional[Dict[str, Any]] = None


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


def _normalize_export_format(fmt: str) -> str:
    normalized = str(fmt or "json").strip().lower()
    if normalized not in {"json", "csv", "markdown"}:
        raise HTTPException(status_code=400, detail="format must be one of: json, csv, markdown")
    return normalized


def _export_response(
    *,
    payload: Dict[str, Any] | str,
    fmt: str,
    stem: str,
):
    if fmt == "json":
        return JSONResponse(
            content=payload,
            headers={"content-disposition": f'attachment; filename="{stem}.json"'},
        )
    if fmt == "csv":
        return PlainTextResponse(
            content=str(payload),
            media_type="text/csv; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{stem}.csv"'},
        )
    if fmt == "markdown":
        return PlainTextResponse(
            content=str(payload),
            media_type="text/markdown; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{stem}.md"'},
        )
    raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")


@subcontracting_router.post("/orders")
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
        raise HTTPException(status_code=400, detail=str(exc))
    return svc.get_order_read_model(order.id)


@subcontracting_router.get("/orders")
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


@subcontracting_router.get("/orders/{order_id}")
async def get_order(order_id: str, db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    try:
        return svc.get_order_read_model(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@subcontracting_router.post("/orders/{order_id}/assign-vendor")
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
        raise HTTPException(status_code=400, detail=str(exc))
    return svc.get_order_read_model(order.id)


@subcontracting_router.post("/orders/{order_id}/issue-material")
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
        raise HTTPException(status_code=400, detail=str(exc))
    return _event_dict(event)


@subcontracting_router.post("/orders/{order_id}/record-receipt")
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
        raise HTTPException(status_code=400, detail=str(exc))
    return _event_dict(event)


@subcontracting_router.get("/orders/{order_id}/timeline")
async def get_timeline(order_id: str, db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    order = svc.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="SubcontractOrder not found")
    events = svc.get_timeline(order_id)
    return {"total": len(events), "events": [_event_dict(event) for event in events]}


@subcontracting_router.get("/overview")
async def subcontracting_overview(db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    return svc.get_overview()


@subcontracting_router.get("/vendors/analytics")
async def subcontracting_vendor_analytics(db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    return svc.get_vendor_analytics()


@subcontracting_router.get("/receipts/analytics")
async def subcontracting_receipt_analytics(db: Session = Depends(get_db)):
    svc = SubcontractingService(db)
    return svc.get_receipt_analytics()


@subcontracting_router.get("/export/overview")
async def export_subcontracting_overview(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.export_overview(fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(payload=payload, fmt=format, stem="subcontracting-overview")


@subcontracting_router.get("/export/vendors")
async def export_subcontracting_vendors(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.export_vendor_analytics(fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(payload=payload, fmt=format, stem="subcontracting-vendors")


@subcontracting_router.get("/export/receipts")
async def export_subcontracting_receipts(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.export_receipt_analytics(fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(payload=payload, fmt=format, stem="subcontracting-receipts")


@subcontracting_router.post("/approval-role-mappings")
async def upsert_subcontracting_approval_role_mapping(
    req: ApprovalRoleMappingRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        svc.upsert_approval_role_mapping(
            role_code=req.role_code,
            scope_type=req.scope_type,
            scope_value=req.scope_value,
            scope_vendor_id=req.scope_vendor_id,
            scope_policy_code=req.scope_policy_code,
            owner=req.owner,
            team=req.team,
            required=req.required,
            sequence=req.sequence,
            fallback_role=req.fallback_role,
            active=req.active,
            properties=req.properties,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    payload = svc.get_approval_role_mapping_registry()
    payload["urls"] = {
        "self": "/api/v1/subcontracting/approval-role-mappings",
        "export": "/api/v1/subcontracting/approval-role-mappings/export?format=json",
    }
    return payload


@subcontracting_router.get("/approval-role-mappings")
async def subcontracting_approval_role_mapping_registry(
    scope_type: Optional[str] = Query(None),
    scope_value: Optional[str] = Query(None),
    scope_vendor_id: Optional[str] = Query(None),
    scope_policy_code: Optional[str] = Query(None),
    role_code: Optional[str] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(200, ge=1, le=500),
    sort_by: str = Query("scope"),
    db: Session = Depends(get_db),
):
    svc = SubcontractingService(db)
    try:
        payload = svc.get_approval_role_mapping_registry(
            scope_type=scope_type,
            scope_value=scope_value,
            scope_vendor_id=scope_vendor_id,
            scope_policy_code=scope_policy_code,
            role_code=role_code,
            active_only=active_only,
            limit=limit,
            sort_by=sort_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    payload["urls"] = {
        "self": "/api/v1/subcontracting/approval-role-mappings",
        "export": "/api/v1/subcontracting/approval-role-mappings/export?format=json",
    }
    return payload


@subcontracting_router.get("/approval-role-mappings/export")
async def export_subcontracting_approval_role_mapping_registry(
    format: str = Query("json"),
    scope_type: Optional[str] = Query(None),
    scope_value: Optional[str] = Query(None),
    scope_vendor_id: Optional[str] = Query(None),
    scope_policy_code: Optional[str] = Query(None),
    role_code: Optional[str] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(200, ge=1, le=500),
    sort_by: str = Query("scope"),
    db: Session = Depends(get_db),
):
    normalized_format = _normalize_export_format(format)
    svc = SubcontractingService(db)
    try:
        payload = svc.export_approval_role_mapping_registry(
            fmt=normalized_format,
            scope_type=scope_type,
            scope_value=scope_value,
            scope_vendor_id=scope_vendor_id,
            scope_policy_code=scope_policy_code,
            role_code=role_code,
            active_only=active_only,
            limit=limit,
            sort_by=sort_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _export_response(
        payload=payload,
        fmt=normalized_format,
        stem="subcontracting-approval-role-mappings",
    )
