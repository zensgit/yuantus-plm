"""PLM Box occupancy and turnover endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_turnover_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_turnover_router.get("/occupancy/overview")
def box_occupancy_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.occupancy_overview()


@box_turnover_router.get("/turnover/summary")
def box_turnover_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.turnover_summary()


@box_turnover_router.get("/items/{box_id}/turnover")
def box_item_turnover(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_turnover(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_turnover_router.get("/export/turnover")
def box_export_turnover(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_turnover()
