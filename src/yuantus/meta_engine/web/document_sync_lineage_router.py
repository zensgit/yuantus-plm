"""
Document sync baseline and lineage router.

R5 of document-sync router decomposition moves the C33 baseline/lineage read
surface out of the legacy document_sync_router without changing public paths.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_lineage_router = APIRouter(
    prefix="/document-sync",
    tags=["Document Sync"],
)


@document_sync_lineage_router.get("/baseline/overview")
def baseline_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.baseline_overview()


@document_sync_lineage_router.get("/sites/{site_id}/lineage")
def site_lineage(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.site_lineage(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@document_sync_lineage_router.get("/jobs/{job_id}/snapshot-lineage")
def job_snapshot_lineage(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.job_snapshot_lineage(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@document_sync_lineage_router.get("/export/lineage")
def export_lineage(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_lineage()
