"""
Document sync analytics and export router.

R1 of document-sync router decomposition moves the C21 read-only analytics
surface out of the legacy document_sync_router without changing public paths.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_analytics_router = APIRouter(
    prefix="/document-sync",
    tags=["Document Sync"],
)


@document_sync_analytics_router.get("/overview")
def sync_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.overview()


@document_sync_analytics_router.get("/sites/{site_id}/analytics")
def site_analytics(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.site_analytics(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_analytics_router.get("/jobs/{job_id}/conflicts")
def job_conflicts(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.job_conflicts(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_analytics_router.get("/export/overview")
def export_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_overview()


@document_sync_analytics_router.get("/export/conflicts")
def export_conflicts(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_conflicts()
