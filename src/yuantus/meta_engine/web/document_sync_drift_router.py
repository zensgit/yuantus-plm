"""
Document sync drift and snapshots router.

R4 of document-sync router decomposition moves the C30 drift/snapshots read
surface out of the legacy document_sync_router without changing public paths.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_drift_router = APIRouter(
    prefix="/document-sync",
    tags=["Document Sync"],
)


@document_sync_drift_router.get("/drift/overview")
def drift_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.drift_overview()


@document_sync_drift_router.get("/sites/{site_id}/snapshots")
def site_snapshots(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.site_snapshots(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_drift_router.get("/jobs/{job_id}/drift")
def job_drift(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.job_drift(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_drift_router.get("/export/drift")
def export_drift(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_drift()
