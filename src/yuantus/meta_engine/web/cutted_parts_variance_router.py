"""Cutted-parts variance and recommendation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_variance_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_variance_router.get("/variance/overview")
def variance_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.variance_overview()


@cutted_parts_variance_router.get("/plans/{plan_id}/recommendations")
def plan_recommendations(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.plan_recommendations(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@cutted_parts_variance_router.get("/materials/variance")
def material_variance(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_variance()


@cutted_parts_variance_router.get("/export/recommendations")
def export_recommendations(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_recommendations()
