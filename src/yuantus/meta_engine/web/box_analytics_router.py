"""PLM Box analytics and contents export endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_analytics_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_analytics_router.get("/overview")
def box_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.overview()


@box_analytics_router.get("/materials/analytics")
def box_material_analytics(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.material_analytics()


@box_analytics_router.get("/items/{box_id}/contents-summary")
def box_contents_summary(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.contents_summary(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@box_analytics_router.get("/export/overview")
def box_export_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_overview()


@box_analytics_router.get("/items/{box_id}/export-contents")
def box_export_contents(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.export_contents(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
