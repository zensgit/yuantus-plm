"""Cutted-parts cost and utilization endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_utilization_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_utilization_router.get("/utilization/overview")
def utilization_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.utilization_overview()


@cutted_parts_utilization_router.get("/materials/utilization")
def material_utilization(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_utilization()


@cutted_parts_utilization_router.get("/plans/{plan_id}/cost-summary")
def plan_cost_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.plan_cost_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@cutted_parts_utilization_router.get("/export/utilization")
def export_utilization(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_utilization()


@cutted_parts_utilization_router.get("/export/costs")
def export_costs(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_costs()
