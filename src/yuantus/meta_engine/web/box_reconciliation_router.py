"""PLM Box reconciliation and audit endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_reconciliation_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_reconciliation_router.get("/reconciliation/overview")
def box_reconciliation_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.reconciliation_overview()


@box_reconciliation_router.get("/audit/summary")
def box_audit_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.audit_summary()


@box_reconciliation_router.get("/items/{box_id}/reconciliation")
def box_item_reconciliation(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_reconciliation(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_reconciliation_router.get("/export/reconciliation")
def box_export_reconciliation(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_box_reconciliation()
