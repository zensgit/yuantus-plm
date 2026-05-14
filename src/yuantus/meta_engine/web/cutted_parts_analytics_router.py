"""Cutted-parts overview, material analytics, and waste export endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_analytics_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_analytics_router.get("/overview")
def cutted_parts_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.overview()


@cutted_parts_analytics_router.get("/materials/analytics")
def material_analytics(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_analytics()


@cutted_parts_analytics_router.get("/plans/{plan_id}/waste-summary")
def waste_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.waste_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@cutted_parts_analytics_router.get("/export/overview")
def export_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_overview()


@cutted_parts_analytics_router.get("/export/waste")
def export_waste(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_waste()
