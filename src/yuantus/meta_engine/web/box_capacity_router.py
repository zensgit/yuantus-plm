"""PLM Box capacity and compliance endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_capacity_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_capacity_router.get("/capacity/overview")
def box_capacity_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.capacity_overview()


@box_capacity_router.get("/compliance/summary")
def box_compliance_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.compliance_summary()


@box_capacity_router.get("/items/{box_id}/capacity")
def box_item_capacity(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_capacity(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@box_capacity_router.get("/export/capacity")
def box_export_capacity(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_capacity()
