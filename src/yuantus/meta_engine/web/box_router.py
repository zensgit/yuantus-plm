"""
PLM Box / Packaging router.

Provides CRUD and query endpoints for box items and their contents.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.models import BoxContent, BoxItem
from yuantus.meta_engine.box.service import BoxService

box_router = APIRouter(prefix="/box", tags=["PLM Box"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BoxCreateRequest(BaseModel):
    name: str
    box_type: str = "box"
    description: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    dimension_unit: str = "mm"
    tare_weight: Optional[float] = None
    max_gross_weight: Optional[float] = None
    weight_unit: str = "kg"
    material: Optional[str] = None
    barcode: Optional[str] = None
    max_quantity: Optional[int] = None
    cost: Optional[float] = None
    product_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _box_dict(box: BoxItem) -> Dict[str, Any]:
    return {
        "id": box.id,
        "name": box.name,
        "description": box.description,
        "box_type": box.box_type,
        "state": box.state,
        "width": box.width,
        "height": box.height,
        "depth": box.depth,
        "dimension_unit": box.dimension_unit,
        "tare_weight": box.tare_weight,
        "max_gross_weight": box.max_gross_weight,
        "weight_unit": box.weight_unit,
        "material": box.material,
        "barcode": box.barcode,
        "max_quantity": box.max_quantity,
        "cost": box.cost,
        "product_id": box.product_id,
        "is_active": box.is_active,
    }


def _content_dict(content: BoxContent) -> Dict[str, Any]:
    return {
        "id": content.id,
        "box_id": content.box_id,
        "item_id": content.item_id,
        "quantity": content.quantity,
        "lot_serial": content.lot_serial,
        "note": content.note,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@box_router.post("/items")
def create_box_item(
    request: BoxCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        box = service.create_box(
            name=request.name,
            box_type=request.box_type,
            description=request.description,
            width=request.width,
            height=request.height,
            depth=request.depth,
            dimension_unit=request.dimension_unit,
            tare_weight=request.tare_weight,
            max_gross_weight=request.max_gross_weight,
            weight_unit=request.weight_unit,
            material=request.material,
            barcode=request.barcode,
            max_quantity=request.max_quantity,
            cost=request.cost,
            product_id=request.product_id,
            properties=request.properties,
            created_by_id=user.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, **_box_dict(box)}


@box_router.get("/items")
def list_box_items(
    box_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    boxes = service.list_boxes(box_type=box_type, state=state, product_id=product_id)
    return {"items": [_box_dict(b) for b in boxes], "count": len(boxes)}


@box_router.get("/items/{box_id}")
def get_box_item(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    box = service.get_box(box_id)
    if box is None:
        raise HTTPException(status_code=404, detail=f"Box '{box_id}' not found")
    return _box_dict(box)


@box_router.get("/items/{box_id}/contents")
def list_box_contents(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    box = service.get_box(box_id)
    if box is None:
        raise HTTPException(status_code=404, detail=f"Box '{box_id}' not found")
    contents = service.list_contents(box_id)
    return {"contents": [_content_dict(c) for c in contents], "count": len(contents)}


@box_router.get("/items/{box_id}/export-meta")
def export_box_meta(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        meta = service.export_meta(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return meta


# ---------------------------------------------------------------------------
# Analytics / export endpoints (C20)
# ---------------------------------------------------------------------------


@box_router.get("/overview")
def box_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.overview()


@box_router.get("/materials/analytics")
def box_material_analytics(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.material_analytics()


@box_router.get("/items/{box_id}/contents-summary")
def box_contents_summary(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.contents_summary(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/overview")
def box_export_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_overview()


@box_router.get("/items/{box_id}/export-contents")
def box_export_contents(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.export_contents(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Ops report / transitions (C23)
# ---------------------------------------------------------------------------


@box_router.get("/transitions/summary")
def box_transition_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.transition_summary()


@box_router.get("/active-archive/breakdown")
def box_active_archive_breakdown(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.active_archive_breakdown()


@box_router.get("/items/{box_id}/ops-report")
def box_ops_report(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.ops_report(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/ops-report")
def box_export_ops_report(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_ops_report()


# ---------------------------------------------------------------------------
# Reconciliation / audit (C26)
# ---------------------------------------------------------------------------


@box_router.get("/reconciliation/overview")
def box_reconciliation_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.reconciliation_overview()


@box_router.get("/audit/summary")
def box_audit_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.audit_summary()


@box_router.get("/items/{box_id}/reconciliation")
def box_item_reconciliation(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_reconciliation(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/reconciliation")
def box_export_reconciliation(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_box_reconciliation()


# ---------------------------------------------------------------------------
# Capacity / Compliance endpoints (C29)
# ---------------------------------------------------------------------------


@box_router.get("/capacity/overview")
def box_capacity_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.capacity_overview()


@box_router.get("/compliance/summary")
def box_compliance_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.compliance_summary()


@box_router.get("/items/{box_id}/capacity")
def box_item_capacity(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_capacity(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/capacity")
def box_export_capacity(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_capacity()


# ---------------------------------------------------------------------------
# Policy / Exceptions endpoints (C32)
# ---------------------------------------------------------------------------


@box_router.get("/policy/overview")
def box_policy_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.policy_overview()


@box_router.get("/exceptions/summary")
def box_exceptions_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.exceptions_summary()


@box_router.get("/items/{box_id}/policy-check")
def box_policy_check(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_policy_check(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/exceptions")
def box_export_exceptions(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_exceptions()


# ---------------------------------------------------------------------------
# Reservations / Traceability endpoints (C35)
# ---------------------------------------------------------------------------


@box_router.get("/reservations/overview")
def box_reservations_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.reservations_overview()


@box_router.get("/traceability/summary")
def box_traceability_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.traceability_summary()


@box_router.get("/items/{box_id}/reservations")
def box_item_reservations(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_reservations(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/traceability")
def box_export_traceability(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_traceability()


# ---------------------------------------------------------------------------
# Allocation / Custody endpoints (C38)
# ---------------------------------------------------------------------------


@box_router.get("/allocations/overview")
def box_allocations_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.allocations_overview()


@box_router.get("/custody/summary")
def box_custody_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.custody_summary()


@box_router.get("/items/{box_id}/custody")
def box_item_custody(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_custody(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/custody")
def box_export_custody(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_custody()


# ---------------------------------------------------------------------------
# Occupancy / Turnover endpoints (C41)
# ---------------------------------------------------------------------------


@box_router.get("/occupancy/overview")
def box_occupancy_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.occupancy_overview()


@box_router.get("/turnover/summary")
def box_turnover_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.turnover_summary()


@box_router.get("/items/{box_id}/turnover")
def box_item_turnover(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_turnover(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_router.get("/export/turnover")
def box_export_turnover(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_turnover()
