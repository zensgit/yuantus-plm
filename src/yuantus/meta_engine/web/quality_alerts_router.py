"""Quality alert API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.quality.service import QualityService
from yuantus.meta_engine.web.quality_common import (
    QualityAlertCreateRequest,
    QualityAlertTransitionRequest,
    alert_to_dict,
)

quality_alerts_router = APIRouter(prefix="/quality", tags=["Quality"])


@quality_alerts_router.post("/alerts")
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
    return alert_to_dict(alert)


@quality_alerts_router.post("/alerts/{alert_id}/transition")
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
    return alert_to_dict(alert)


@quality_alerts_router.get("/alerts")
async def list_quality_alerts(
    state: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    alerts = svc.list_alerts(state=state, priority=priority, product_id=product_id)
    return {"total": len(alerts), "alerts": [alert_to_dict(alert) for alert in alerts]}


@quality_alerts_router.get("/alerts/{alert_id}")
async def get_quality_alert(alert_id: str, db: Session = Depends(get_db)):
    svc = QualityService(db)
    alert = svc.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Quality alert not found")
    return alert_to_dict(alert)


@quality_alerts_router.get("/alerts/{alert_id}/manufacturing-context")
async def get_alert_manufacturing_context(
    alert_id: str,
    db: Session = Depends(get_db),
):
    svc = QualityService(db)
    ctx = svc.get_alert_manufacturing_context(alert_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Quality alert not found")
    return ctx
