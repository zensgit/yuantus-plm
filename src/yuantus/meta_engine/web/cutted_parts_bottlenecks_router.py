"""Cutted-parts saturation and bottleneck endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_bottlenecks_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_bottlenecks_router.get("/saturation/overview")
def saturation_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.saturation_overview()


@cutted_parts_bottlenecks_router.get("/bottlenecks/summary")
def bottlenecks_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.bottlenecks_summary()


@cutted_parts_bottlenecks_router.get("/plans/{plan_id}/bottlenecks")
def plan_bottlenecks(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.plan_bottlenecks(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@cutted_parts_bottlenecks_router.get("/export/bottlenecks")
def export_bottlenecks(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_bottlenecks()
