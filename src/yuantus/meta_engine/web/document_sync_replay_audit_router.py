"""
Document sync replay and audit router.

R3 of document-sync router decomposition moves the C27 replay/audit read
surface out of the legacy document_sync_router without changing public paths.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_replay_audit_router = APIRouter(
    prefix="/document-sync",
    tags=["Document Sync"],
)


@document_sync_replay_audit_router.get("/replay/overview")
def replay_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.replay_overview()


@document_sync_replay_audit_router.get("/sites/{site_id}/audit")
def site_audit(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.site_audit(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_replay_audit_router.get("/jobs/{job_id}/audit")
def job_audit(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.job_audit(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_replay_audit_router.get("/export/audit")
def export_audit(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_audit()
