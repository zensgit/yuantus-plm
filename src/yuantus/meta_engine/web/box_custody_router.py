"""PLM Box allocation and custody endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_custody_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_custody_router.get("/allocations/overview")
def box_allocations_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.allocations_overview()


@box_custody_router.get("/custody/summary")
def box_custody_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.custody_summary()


@box_custody_router.get("/items/{box_id}/custody")
def box_item_custody(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_custody(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@box_custody_router.get("/export/custody")
def box_export_custody(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_custody()
