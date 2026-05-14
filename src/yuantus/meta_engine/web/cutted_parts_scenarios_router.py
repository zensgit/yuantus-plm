"""Cutted-parts template and scenario endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_scenarios_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_scenarios_router.get("/templates/overview")
def template_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.template_overview()


@cutted_parts_scenarios_router.get("/plans/{plan_id}/scenarios")
def scenario_summary(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.scenario_summary(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@cutted_parts_scenarios_router.get("/materials/templates")
def material_templates(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.material_templates()


@cutted_parts_scenarios_router.get("/export/scenarios")
def export_scenarios(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_scenarios()
