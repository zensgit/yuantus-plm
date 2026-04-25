"""Cutted-parts alert and outlier endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_alerts_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_alerts_router.get("/alerts/overview")
def alerts_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.alerts_overview()


@cutted_parts_alerts_router.get("/outliers/summary")
def outliers_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.outliers_summary()


@cutted_parts_alerts_router.get("/plans/{plan_id}/alerts")
def plan_alerts(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.plan_alerts(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@cutted_parts_alerts_router.get("/export/outliers")
def export_outliers(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_outliers()
