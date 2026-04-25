"""
Document sync checkpoints and retention router.

R6 of document-sync router decomposition moves the C36 checkpoints/retention
read surface out of the legacy document_sync_router without changing public
paths.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_retention_router = APIRouter(
    prefix="/document-sync",
    tags=["Document Sync"],
)


@document_sync_retention_router.get("/checkpoints/overview")
def checkpoints_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.checkpoints_overview()


@document_sync_retention_router.get("/retention/summary")
def retention_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.retention_summary()


@document_sync_retention_router.get("/sites/{site_id}/checkpoints")
def site_checkpoints(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.site_checkpoints(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_retention_router.get("/export/retention")
def export_retention(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_retention()
