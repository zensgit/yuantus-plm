"""Quality assurance API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.meta_engine.quality.service import QualityService

quality_router = APIRouter(prefix="/quality", tags=["Quality"])


# ============================================================================
# Request / Response Models
# ============================================================================


class QualityPointCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    check_type: str = "pass_fail"
    product_id: Optional[str] = None
    item_type_id: Optional[str] = None
    routing_id: Optional[str] = None
    operation_id: Optional[str] = None
    trigger_on: str = "manual"
    measure_min: Optional[float] = None
    measure_max: Optional[float] = None
    measure_unit: Optional[str] = None
    measure_tolerance: Optional[float] = None
    worksheet_template: Optional[str] = None
    instructions: Optional[str] = None
    team_name: Optional[str] = None
    sequence: int = 10
    properties: Optional[Dict[str, Any]] = None


class QualityPointUpdateRequest(BaseModel):
    name: Optional[str] = None
    check_type: Optional[str] = None
    is_active: Optional[bool] = None
    routing_id: Optional[str] = None
    operation_id: Optional[str] = None
    measure_min: Optional[float] = None
    measure_max: Optional[float] = None
    measure_unit: Optional[str] = None
    instructions: Optional[str] = None
    sequence: Optional[int] = None


class QualityCheckCreateRequest(BaseModel):
    point_id: str
    product_id: Optional[str] = None
    source_document_ref: Optional[str] = None
    lot_serial: Optional[str] = None


class QualityCheckRecordRequest(BaseModel):
    result: str
    measure_value: Optional[float] = None
    picture_path: Optional[str] = None
    worksheet_data: Optional[Dict[str, Any]] = None
    note: Optional[str] = None


class QualityAlertCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    check_id: Optional[str] = None
    product_id: Optional[str] = None
    description: Optional[str] = None
    priority: str = "medium"
    team_name: Optional[str] = None


class QualityAlertTransitionRequest(BaseModel):
    target_state: str


# ============================================================================
# Helper
# ============================================================================

def _point_dict(p) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "check_type": p.check_type,
        "product_id": p.product_id,
        "item_type_id": p.item_type_id,
        "routing_id": p.routing_id,
        "operation_id": p.operation_id,
        "trigger_on": p.trigger_on,
        "measure_min": p.measure_min,
        "measure_max": p.measure_max,
        "measure_unit": p.measure_unit,
        "is_active": p.is_active,
        "sequence": p.sequence,
        "team_name": p.team_name,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _check_dict(c) -> dict:
    return {
        "id": c.id,
        "point_id": c.point_id,
        "product_id": c.product_id,
        "routing_id": c.routing_id,
        "operation_id": c.operation_id,
        "check_type": c.check_type,
        "result": c.result,
        "measure_value": c.measure_value,
        "note": c.note,
        "source_document_ref": c.source_document_ref,
        "lot_serial": c.lot_serial,
        "checked_at": c.checked_at.isoformat() if c.checked_at else None,
        "checked_by_id": c.checked_by_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _alert_dict(a) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "check_id": a.check_id,
        "product_id": a.product_id,
        "state": a.state,
        "priority": a.priority,
        "description": a.description,
        "root_cause": a.root_cause,
        "corrective_action": a.corrective_action,
        "team_name": a.team_name,
        "assigned_user_id": a.assigned_user_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "confirmed_at": a.confirmed_at.isoformat() if a.confirmed_at else None,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "closed_at": a.closed_at.isoformat() if a.closed_at else None,
    }


# ============================================================================
# Quality Point Endpoints
# ============================================================================


@quality_router.post("/points")
async def create_quality_point(
    req: QualityPointCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        point = svc.create_point(
            name=req.name,
            check_type=req.check_type,
            product_id=req.product_id,
            item_type_id=req.item_type_id,
            routing_id=req.routing_id,
            operation_id=req.operation_id,
            trigger_on=req.trigger_on,
            measure_min=req.measure_min,
            measure_max=req.measure_max,
            measure_unit=req.measure_unit,
            measure_tolerance=req.measure_tolerance,
            worksheet_template=req.worksheet_template,
            instructions=req.instructions,
            team_name=req.team_name,
            sequence=req.sequence,
            properties=req.properties,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _point_dict(point)


@quality_router.get("/points")
async def list_quality_points(
    product_id: Optional[str] = Query(None),
    item_type_id: Optional[str] = Query(None),
    routing_id: Optional[str] = Query(None),
    operation_id: Optional[str] = Query(None),
    check_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    points = svc.list_points(
        product_id=product_id,
        item_type_id=item_type_id,
        routing_id=routing_id,
        operation_id=operation_id,
        check_type=check_type,
        is_active=is_active,
    )
    return {"total": len(points), "points": [_point_dict(p) for p in points]}


@quality_router.get("/points/{point_id}")
async def get_quality_point(point_id: str, db: Session = Depends(get_db)):
    svc = QualityService(db)
    point = svc.get_point(point_id)
    if not point:
        raise HTTPException(status_code=404, detail="Quality point not found")
    return _point_dict(point)


@quality_router.patch("/points/{point_id}")
async def update_quality_point(
    point_id: str,
    req: QualityPointUpdateRequest,
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    fields = {k: v for k, v in req.model_dump(exclude_unset=True).items()}
    point = svc.update_point(point_id, **fields)
    if not point:
        raise HTTPException(status_code=404, detail="Quality point not found")
    db.commit()
    return _point_dict(point)


# ============================================================================
# Quality Check Endpoints
# ============================================================================


@quality_router.post("/checks")
async def create_quality_check(
    req: QualityCheckCreateRequest,
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        check = svc.create_check(
            point_id=req.point_id,
            product_id=req.product_id,
            source_document_ref=req.source_document_ref,
            lot_serial=req.lot_serial,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _check_dict(check)


@quality_router.post("/checks/{check_id}/record")
async def record_quality_check(
    check_id: str,
    req: QualityCheckRecordRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        check = svc.record_check_result(
            check_id,
            result=req.result,
            measure_value=req.measure_value,
            picture_path=req.picture_path,
            worksheet_data=req.worksheet_data,
            note=req.note,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _check_dict(check)


@quality_router.get("/checks")
async def list_quality_checks(
    point_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    routing_id: Optional[str] = Query(None),
    operation_id: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    checks = svc.list_checks(
        point_id=point_id,
        product_id=product_id,
        routing_id=routing_id,
        operation_id=operation_id,
        result=result,
    )
    return {"total": len(checks), "checks": [_check_dict(c) for c in checks]}


@quality_router.get("/checks/{check_id}")
async def get_quality_check(check_id: str, db: Session = Depends(get_db)):
    svc = QualityService(db)
    check = svc.get_check(check_id)
    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")
    return _check_dict(check)


# ============================================================================
# Quality Alert Endpoints
# ============================================================================


@quality_router.post("/alerts")
async def create_quality_alert(
    req: QualityAlertCreateRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        alert = svc.create_alert(
            name=req.name,
            check_id=req.check_id,
            product_id=req.product_id,
            description=req.description,
            priority=req.priority,
            team_name=req.team_name,
            user_id=user_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _alert_dict(alert)


@quality_router.post("/alerts/{alert_id}/transition")
async def transition_quality_alert(
    alert_id: str,
    req: QualityAlertTransitionRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    try:
        alert = svc.transition_alert(
            alert_id, target_state=req.target_state, user_id=user_id
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return _alert_dict(alert)


@quality_router.get("/alerts")
async def list_quality_alerts(
    state: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    alerts = svc.list_alerts(state=state, priority=priority, product_id=product_id)
    return {"total": len(alerts), "alerts": [_alert_dict(a) for a in alerts]}


@quality_router.get("/alerts/{alert_id}")
async def get_quality_alert(alert_id: str, db: Session = Depends(get_db)):
    svc = QualityService(db)
    alert = svc.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Quality alert not found")
    return _alert_dict(alert)


@quality_router.get("/alerts/{alert_id}/manufacturing-context")
async def get_alert_manufacturing_context(
    alert_id: str,
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    ctx = svc.get_alert_manufacturing_context(alert_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Quality alert not found")
    return ctx
