"""Cutted-parts threshold and envelope endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_thresholds_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_thresholds_router.get("/thresholds/overview")
def thresholds_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.thresholds_overview()


@cutted_parts_thresholds_router.get("/envelopes/summary")
def envelopes_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.envelopes_summary()


@cutted_parts_thresholds_router.get("/plans/{plan_id}/threshold-check")
def plan_threshold_check(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.plan_threshold_check(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@cutted_parts_thresholds_router.get("/export/envelopes")
def export_envelopes(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_envelopes()
