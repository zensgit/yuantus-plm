"""PLM Box transition and operations report endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_ops_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_ops_router.get("/transitions/summary")
def box_transition_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.transition_summary()


@box_ops_router.get("/active-archive/breakdown")
def box_active_archive_breakdown(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.active_archive_breakdown()


@box_ops_router.get("/items/{box_id}/ops-report")
def box_ops_report(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.ops_report(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_ops_router.get("/export/ops-report")
def box_export_ops_report(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_ops_report()
