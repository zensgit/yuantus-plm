from __future__ import annotations

from datetime import datetime, timezone
import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.parallel_tasks_service import DocumentMultiSiteService


parallel_tasks_doc_sync_router = APIRouter(tags=["ParallelTasks"])


def _error_detail(
    code: str,
    message: str,
    *,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "code": str(code),
        "message": str(message),
        "context": context or {},
    }


def _raise_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=_error_detail(code, message, context=context),
    )


def _parse_utc_datetime(raw: Optional[str], *, field_name: str) -> Optional[datetime]:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _raise_api_error(
            status_code=400,
            code="invalid_datetime",
            message=f"{field_name} must be an ISO-8601 datetime",
            context={"field": field_name, "value": raw},
        )
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


class RemoteSiteUpsertRequest(BaseModel):
    name: str
    endpoint: str
    auth_mode: str = "token"
    auth_secret: Optional[str] = None
    is_active: bool = True
    metadata_json: Optional[Dict[str, Any]] = None


class SyncJobCreateRequest(BaseModel):
    site_id: str
    direction: str = Field(..., description="push|pull")
    document_ids: List[str] = Field(..., min_length=1)
    idempotency_key: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class SyncReplayBatchRequest(BaseModel):
    job_ids: Optional[List[str]] = None
    site_id: Optional[str] = None
    only_dead_letter: bool = True
    window_days: int = Field(7, ge=1, le=90)
    limit: int = Field(50, ge=1, le=500)


@parallel_tasks_doc_sync_router.post("/doc-sync/sites")
async def upsert_remote_site(
    payload: RemoteSiteUpsertRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        site = service.upsert_remote_site(
            name=payload.name,
            endpoint=payload.endpoint,
            auth_mode=payload.auth_mode,
            auth_secret=payload.auth_secret,
            is_active=payload.is_active,
            metadata_json=payload.metadata_json,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="remote_site_upsert_failed",
            message=str(exc),
            context={"name": payload.name},
        )
    return {
        "id": site.id,
        "name": site.name,
        "endpoint": site.endpoint,
        "auth_mode": site.auth_mode,
        "secret_configured": bool(site.auth_secret_ciphertext),
        "is_active": bool(site.is_active),
        "last_health_status": site.last_health_status,
        "last_health_error": site.last_health_error,
        "last_health_at": site.last_health_at.isoformat() if site.last_health_at else None,
        "updated_at": site.updated_at.isoformat() if site.updated_at else None,
        "operator_id": int(user.id),
    }


@parallel_tasks_doc_sync_router.get("/doc-sync/sites")
async def list_remote_sites(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    sites = service.list_remote_sites(active_only=active_only)
    return {
        "total": len(sites),
        "sites": [
            {
                "id": site.id,
                "name": site.name,
                "endpoint": site.endpoint,
                "auth_mode": site.auth_mode,
                "secret_configured": bool(site.auth_secret_ciphertext),
                "is_active": bool(site.is_active),
                "last_health_status": site.last_health_status,
                "last_health_error": site.last_health_error,
                "last_health_at": (
                    site.last_health_at.isoformat() if site.last_health_at else None
                ),
            }
            for site in sites
        ],
        "operator_id": int(user.id),
    }


@parallel_tasks_doc_sync_router.post("/doc-sync/sites/{site_id}/health")
async def check_remote_site_health(
    site_id: str,
    timeout_s: float = Query(3.0, ge=0.5, le=15),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        result = service.probe_remote_site(site_id, timeout_s=timeout_s)
        db.commit()
    except ValueError as exc:
        _raise_api_error(
            status_code=404,
            code="remote_site_not_found",
            message=str(exc),
            context={"site_id": site_id},
        )
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="remote_site_probe_failed",
            message=str(exc),
            context={"site_id": site_id},
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_doc_sync_router.post("/doc-sync/jobs")
async def create_sync_job(
    payload: SyncJobCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        job = service.enqueue_sync(
            site_id=payload.site_id,
            direction=payload.direction,
            document_ids=payload.document_ids,
            user_id=int(user.id),
            idempotency_key=payload.idempotency_key,
            metadata_json=payload.metadata_json,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        detail = str(exc)
        lowered = detail.lower()
        if "not found" in lowered:
            _raise_api_error(
                status_code=404,
                code="remote_site_not_found",
                message=detail,
                context={"site_id": payload.site_id},
            )
        if "inactive" in lowered:
            _raise_api_error(
                status_code=409,
                code="remote_site_inactive",
                message=detail,
                context={"site_id": payload.site_id},
            )
        _raise_api_error(
            status_code=400,
            code="doc_sync_job_invalid",
            message=detail,
            context={
                "site_id": payload.site_id,
                "direction": payload.direction,
            },
        )
    return {
        "job_id": job.id,
        "task_type": job.task_type,
        "status": job.status,
        "dedupe_key": job.dedupe_key,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@parallel_tasks_doc_sync_router.get("/doc-sync/jobs")
async def list_sync_jobs(
    site_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None, description="ISO-8601 datetime"),
    created_to: Optional[str] = Query(None, description="ISO-8601 datetime"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    from_dt = _parse_utc_datetime(created_from, field_name="created_from")
    to_dt = _parse_utc_datetime(created_to, field_name="created_to")
    try:
        jobs = service.list_sync_jobs(
            site_id=site_id,
            status=status,
            created_from=from_dt,
            created_to=to_dt,
            limit=limit,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="doc_sync_filter_invalid",
            message=str(exc),
            context={
                "site_id": site_id,
                "status": status,
                "created_from": created_from,
                "created_to": created_to,
            },
        )
    return {
        "total": len(jobs),
        "jobs": [service.build_sync_job_view(job) for job in jobs],
        "operator_id": int(user.id),
    }


@parallel_tasks_doc_sync_router.get("/doc-sync/jobs/dead-letter")
async def list_doc_sync_dead_letter_jobs(
    site_id: Optional[str] = Query(None),
    window_days: int = Query(7),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        jobs = service.list_dead_letter_sync_jobs(
            site_id=site_id,
            window_days=window_days,
            limit=limit,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="doc_sync_dead_letter_invalid",
            message=str(exc),
            context={"site_id": site_id, "window_days": window_days, "limit": limit},
        )
    return {
        "site_id": site_id,
        "window_days": window_days,
        "total": len(jobs),
        "jobs": [service.build_sync_job_view(job) for job in jobs],
        "operator_id": int(user.id),
    }


@parallel_tasks_doc_sync_router.post("/doc-sync/jobs/replay-batch")
async def replay_doc_sync_jobs_batch(
    payload: SyncReplayBatchRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        result = service.replay_sync_jobs_batch(
            job_ids=payload.job_ids,
            site_id=payload.site_id,
            only_dead_letter=payload.only_dead_letter,
            window_days=payload.window_days,
            limit=payload.limit,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="doc_sync_replay_batch_invalid",
            message=str(exc),
            context={
                "site_id": payload.site_id,
                "only_dead_letter": payload.only_dead_letter,
                "window_days": payload.window_days,
                "limit": payload.limit,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_doc_sync_router.get("/doc-sync/summary")
async def get_doc_sync_summary(
    site_id: Optional[str] = Query(None),
    window_days: int = Query(7),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        result = service.sync_summary(site_id=site_id, window_days=window_days)
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="doc_sync_summary_invalid",
            message=str(exc),
            context={"site_id": site_id, "window_days": window_days},
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_doc_sync_router.get("/doc-sync/summary/export")
async def export_doc_sync_summary(
    site_id: Optional[str] = Query(None),
    window_days: int = Query(7),
    export_format: str = Query("json", description="json|csv|md"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        exported = service.export_sync_summary(
            site_id=site_id,
            window_days=window_days,
            export_format=export_format,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="doc_sync_summary_export_invalid",
            message=str(exc),
            context={
                "site_id": site_id,
                "window_days": window_days,
                "export_format": export_format,
            },
        )
    return StreamingResponse(
        io.BytesIO(exported["content"]),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "doc-sync-summary.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


@parallel_tasks_doc_sync_router.get("/doc-sync/jobs/{job_id}")
async def get_sync_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    job = service.get_sync_job(job_id)
    if not job:
        _raise_api_error(
            status_code=404,
            code="doc_sync_job_not_found",
            message=f"Sync job not found: {job_id}",
            context={"job_id": job_id},
        )
    result = service.build_sync_job_view(job)
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_doc_sync_router.post("/doc-sync/jobs/{job_id}/replay")
async def replay_sync_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    try:
        new_job = service.replay_sync_job(job_id, user_id=int(user.id))
        db.commit()
    except ValueError as exc:
        _raise_api_error(
            status_code=404,
            code="doc_sync_job_not_found",
            message=str(exc),
            context={"job_id": job_id},
        )
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="doc_sync_replay_failed",
            message=str(exc),
            context={"job_id": job_id},
        )
    return {
        "job_id": new_job.id,
        "task_type": new_job.task_type,
        "status": new_job.status,
        "dedupe_key": new_job.dedupe_key,
        "replay_of": job_id,
    }
