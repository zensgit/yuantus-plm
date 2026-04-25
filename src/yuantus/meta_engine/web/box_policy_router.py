"""PLM Box policy and exception endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.box.service import BoxService


box_policy_router = APIRouter(prefix="/box", tags=["PLM Box"])


@box_policy_router.get("/policy/overview")
def box_policy_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.policy_overview()


@box_policy_router.get("/exceptions/summary")
def box_exceptions_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.exceptions_summary()


@box_policy_router.get("/items/{box_id}/policy-check")
def box_policy_check(
    box_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    try:
        return service.box_policy_check(box_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@box_policy_router.get("/export/exceptions")
def box_export_exceptions(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BoxService(db)
    return service.export_exceptions()
