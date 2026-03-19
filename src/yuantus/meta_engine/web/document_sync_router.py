"""
Document Multi-Site Sync router.

Provides site management, sync job lifecycle, and summary endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.models import SyncJob, SyncSite
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_router = APIRouter(prefix="/document-sync", tags=["Document Sync"])


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class SiteCreateRequest(BaseModel):
    name: str
    site_code: str
    base_url: Optional[str] = None
    description: Optional[str] = None
    direction: str = "push"
    is_primary: bool = False
    properties: Optional[Dict[str, Any]] = None


class JobCreateRequest(BaseModel):
    site_id: str
    direction: str = "push"
    document_filter: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _site_dict(site: SyncSite) -> Dict[str, Any]:
    return {
        "id": site.id,
        "name": site.name,
        "description": site.description,
        "base_url": site.base_url,
        "site_code": site.site_code,
        "state": site.state,
        "direction": site.direction,
        "is_primary": site.is_primary,
    }


def _job_dict(job: SyncJob) -> Dict[str, Any]:
    return {
        "id": job.id,
        "site_id": job.site_id,
        "state": job.state,
        "direction": job.direction,
        "total_documents": job.total_documents,
        "synced_count": job.synced_count,
        "conflict_count": job.conflict_count,
        "error_count": job.error_count,
        "skipped_count": job.skipped_count,
    }


# ---------------------------------------------------------------------------
# Site endpoints
# ---------------------------------------------------------------------------


@document_sync_router.post("/sites")
def create_site(
    request: SiteCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        site = service.create_site(
            name=request.name,
            site_code=request.site_code,
            base_url=request.base_url,
            description=request.description,
            direction=request.direction,
            is_primary=request.is_primary,
            properties=request.properties,
            created_by_id=user.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, **_site_dict(site)}


@document_sync_router.get("/sites")
def list_sites(
    state: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    sites = service.list_sites(state=state, direction=direction)
    return {"sites": [_site_dict(s) for s in sites], "count": len(sites)}


@document_sync_router.get("/sites/{site_id}")
def get_site(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    site = service.get_site(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found")
    return _site_dict(site)


# ---------------------------------------------------------------------------
# Job endpoints
# ---------------------------------------------------------------------------


@document_sync_router.post("/jobs")
def create_job(
    request: JobCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        job = service.create_job(
            site_id=request.site_id,
            direction=request.direction,
            document_filter=request.document_filter,
            properties=request.properties,
            created_by_id=user.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, **_job_dict(job)}


@document_sync_router.get("/jobs")
def list_jobs(
    site_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    jobs = service.list_jobs(site_id=site_id, state=state)
    return {"jobs": [_job_dict(j) for j in jobs], "count": len(jobs)}


@document_sync_router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return _job_dict(job)


@document_sync_router.get("/jobs/{job_id}/summary")
def get_job_summary(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        summary = service.job_summary(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return summary


# ---------------------------------------------------------------------------
# Analytics / export endpoints (C21)
# ---------------------------------------------------------------------------


@document_sync_router.get("/overview")
def sync_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.overview()


@document_sync_router.get("/sites/{site_id}/analytics")
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


@document_sync_router.get("/jobs/{job_id}/conflicts")
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


@document_sync_router.get("/export/overview")
def export_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_overview()


@document_sync_router.get("/export/conflicts")
def export_conflicts(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_conflicts()


# ---------------------------------------------------------------------------
# Reconciliation endpoints (C24)
# ---------------------------------------------------------------------------


@document_sync_router.get("/reconciliation/queue")
def reconciliation_queue(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.reconciliation_queue()


@document_sync_router.get("/reconciliation/jobs/{job_id}/summary")
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


@document_sync_router.get("/reconciliation/sites/{site_id}/status")
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


@document_sync_router.get("/export/reconciliation")
def export_reconciliation(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_reconciliation()


# ---------------------------------------------------------------------------
# Replay / audit endpoints (C27)
# ---------------------------------------------------------------------------


@document_sync_router.get("/replay/overview")
def replay_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.replay_overview()


@document_sync_router.get("/sites/{site_id}/audit")
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


@document_sync_router.get("/jobs/{job_id}/audit")
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


@document_sync_router.get("/export/audit")
def export_audit(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_audit()


# ---------------------------------------------------------------------------
# Drift / Snapshots endpoints (C30)
# ---------------------------------------------------------------------------


@document_sync_router.get("/drift/overview")
def drift_overview(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.drift_overview()


@document_sync_router.get("/sites/{site_id}/snapshots")
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


@document_sync_router.get("/jobs/{job_id}/drift")
def job_drift_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        return service.job_drift(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@document_sync_router.get("/export/drift")
def export_drift(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    return service.export_drift()
