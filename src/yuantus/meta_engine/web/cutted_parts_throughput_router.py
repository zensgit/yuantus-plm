"""Cutted-parts throughput and cadence endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.cutted_parts.service import CuttedPartsService


cutted_parts_throughput_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])


@cutted_parts_throughput_router.get("/throughput/overview")
def throughput_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.throughput_overview()


@cutted_parts_throughput_router.get("/cadence/summary")
def cadence_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.cadence_summary()


@cutted_parts_throughput_router.get("/plans/{plan_id}/cadence")
def plan_cadence(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    try:
        return service.plan_cadence(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@cutted_parts_throughput_router.get("/export/cadence")
def export_cadence(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = CuttedPartsService(db)
    return service.export_cadence()
