"""PLM Box dwell and aging endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_aging_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_aging_router.get("/dwell/overview")
def box_dwell_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.dwell_overview()


@box_aging_router.get("/aging/summary")
def box_aging_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.aging_summary()


@box_aging_router.get("/items/{box_id}/aging")
def box_item_aging(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_aging(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@box_aging_router.get("/export/aging")
def box_export_aging(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_aging()
