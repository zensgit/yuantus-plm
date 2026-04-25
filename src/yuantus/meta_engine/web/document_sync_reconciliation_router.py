"""
Document sync reconciliation router.

R2 of document-sync router decomposition moves the C24 reconciliation read
surface out of the legacy document_sync_router without changing public paths.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_reconciliation_router = APIRouter(
    prefix="/document-sync",
    tags=["Document Sync"],
)


@document_sync_reconciliation_router.get("/reconciliation/queue")
def reconciliation_queue(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.reconciliation_queue()


@document_sync_reconciliation_router.get("/reconciliation/jobs/{job_id}/summary")
def reconciliation_job_summary(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.conflict_resolution_summary(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_reconciliation_router.get("/reconciliation/sites/{site_id}/status")
def reconciliation_site_status(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.site_reconciliation_status(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_reconciliation_router.get("/export/reconciliation")
def export_reconciliation(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_reconciliation()
