"""PLM Box reservation and traceability endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_traceability_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_traceability_router.get("/reservations/overview")
def box_reservations_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.reservations_overview()


@box_traceability_router.get("/traceability/summary")
def box_traceability_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.traceability_summary()


@box_traceability_router.get("/items/{box_id}/reservations")
def box_item_reservations(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_reservations(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@box_traceability_router.get("/export/traceability")
def box_export_traceability(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_traceability()
