"""
Document sync core site, mirror, and job router.

R8 of document-sync router decomposition moves the remaining core runtime
surface out of the legacy document_sync_router while preserving public paths.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.document_sync.models import SyncJob, SyncSite
from yuantus.meta_engine.document_sync.service import DocumentSyncService

document_sync_core_router = APIRouter(prefix="/document-sync", tags=["Document Sync"])


class SiteCreateRequest(BaseModel):
    name: str
    site_code: str
    base_url: Optional[str] = None
    description: Optional[str] = None
    direction: str = "push"
    is_primary: bool = False
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


class JobCreateRequest(BaseModel):
    site_id: str
    direction: str = "push"
    document_filter: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


def _site_dict(site: SyncSite) -> Dict[str, Any]:
    auth_type = getattr(site, "auth_type", None)
    auth_config = getattr(site, "auth_config", None) or {}
    masked_auth_config: Optional[Dict[str, Any]] = None
    if auth_type == "basic":
        masked_auth_config = {
            "username": auth_config.get("username"),
            "has_password": bool(auth_config.get("password")),
        }

    return {
        "id": site.id,
        "name": site.name,
        "description": site.description,
        "base_url": site.base_url,
        "site_code": site.site_code,
        "state": site.state,
        "auth_type": auth_type,
        "auth_config": masked_auth_config,
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


@document_sync_core_router.post("/sites")
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
            auth_type=request.auth_type,
            auth_config=request.auth_config,
            direction=request.direction,
            is_primary=request.is_primary,
            properties=request.properties,
            created_by_id=user.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **_site_dict(site)}


@document_sync_core_router.get("/sites")
def list_sites(
    state: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    sites = service.list_sites(state=state, direction=direction)
    return {"sites": [_site_dict(s) for s in sites], "count": len(sites)}


@document_sync_core_router.get("/sites/{site_id}")
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


@document_sync_core_router.post("/sites/{site_id}/mirror-probe")
def mirror_probe_site(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """BasicAuth outbound mirror probe for a sync site.

    Returns probe outcome (status_code, endpoint, remote_overview if JSON).
    All validation / connectivity / auth failures map to HTTP 400.
    Password is never echoed in the response.
    """
    service = DocumentSyncService(db)
    try:
        result = service.mirror_probe(site_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@document_sync_core_router.post("/sites/{site_id}/mirror-execute")
def mirror_execute_site(
    site_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """BasicAuth outbound mirror execute for a sync site.

    Creates a local SyncJob, calls the remote overview endpoint with BasicAuth,
    maps the remote payload onto job aggregates, and transitions the job to
    ``completed`` or ``failed``.
    """
    service = DocumentSyncService(db)
    try:
        result = service.mirror_execute(site_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@document_sync_core_router.post("/jobs")
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, **_job_dict(job)}


@document_sync_core_router.get("/jobs")
def list_jobs(
    site_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    jobs = service.list_jobs(site_id=site_id, state=state)
    return {"jobs": [_job_dict(j) for j in jobs], "count": len(jobs)}


@document_sync_core_router.get("/jobs/{job_id}")
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


@document_sync_core_router.get("/jobs/{job_id}/summary")
def get_job_summary(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentSyncService(db)
    try:
        summary = service.job_summary(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return summary
