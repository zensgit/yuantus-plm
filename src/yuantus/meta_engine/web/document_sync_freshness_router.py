"""
Document sync freshness and watermarks router.

R7 of document-sync router decomposition moves the C39 freshness/watermarks
read surface out of the legacy document_sync_router without changing public
paths.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_freshness_router = APIRouter(
    prefix="/document-sync",
    tags=["Document Sync"],
)


@document_sync_freshness_router.get("/freshness/overview")
def freshness_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.freshness_overview()


@document_sync_freshness_router.get("/watermarks/summary")
def watermarks_summary(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.watermarks_summary()


@document_sync_freshness_router.get("/sites/{site_id}/freshness")
def site_freshness(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.site_freshness(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@document_sync_freshness_router.get("/export/watermarks")
def export_watermarks(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_watermarks()
