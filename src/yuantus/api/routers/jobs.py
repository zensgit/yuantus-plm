from __future__ import annotations

from datetime import datetime
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.storage.local_storage import LocalStorageProvider
from yuantus.config import get_settings
from yuantus.meta_engine.services.job_service import JobService
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.quota_service import QuotaService
from yuantus.exceptions.handlers import QuotaExceededError

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class CreateJobRequest(BaseModel):
    task_type: str = Field(..., description="Task type, e.g. cad_conversion")
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=10, description="Lower is higher priority")
    max_attempts: Optional[int] = Field(default=None, description="Override max attempts")
    dedupe_key: Optional[str] = Field(default=None, description="Optional dedupe key")
    dedupe: bool = Field(default=False, description="Enable dedupe by key or payload")


class JobResponse(BaseModel):
    id: str
    task_type: str
    payload: Dict[str, Any]
    status: str
    priority: int
    worker_id: Optional[str] = None
    attempt_count: int
    max_attempts: int
    last_error: Optional[str] = None
    dedupe_key: Optional[str] = None
    created_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    diagnostics: Optional[Dict[str, Any]] = None


def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(payload or {})
    if "authorization" in cleaned:
        cleaned["authorization"] = "<redacted>"
    if "Authorization" in cleaned:
        cleaned["Authorization"] = "<redacted>"
    return cleaned


def _json_text(expr):
    if hasattr(expr, "as_string"):
        return expr.as_string()
    if hasattr(expr, "astext"):
        return expr.astext
    return cast(expr, String)


def _build_job_diagnostics(job: ConversionJob, db: Session) -> Optional[Dict[str, Any]]:
    payload = job.payload or {}
    file_id = payload.get("file_id")
    if not file_id:
        return None

    diagnostics: Dict[str, Any] = {"file_id": file_id}
    file_container = db.get(FileContainer, str(file_id))
    if not file_container:
        diagnostics["file_missing"] = True
        if job.last_error:
            diagnostics["last_error"] = job.last_error
        if payload.get("error"):
            diagnostics["error"] = payload.get("error")
        return diagnostics

    settings = get_settings()
    file_service = FileService()
    system_path = file_container.system_path
    resolved_source_path: Optional[str] = None
    if isinstance(file_service.storage_provider, LocalStorageProvider):
        resolved_source_path = file_service.storage_provider.get_local_path(system_path)
    elif settings.STORAGE_TYPE == "s3" and system_path:
        resolved_source_path = f"s3://{settings.S3_BUCKET_NAME}/{system_path}"

    diagnostics.update(
        {
            "storage_type": settings.STORAGE_TYPE,
            "system_path": system_path,
            "resolved_source_path": resolved_source_path,
            "cad_connector_id": file_container.cad_connector_id,
            "cad_format": file_container.cad_format,
            "document_type": file_container.document_type,
            "preview_path": file_container.preview_path,
            "geometry_path": file_container.geometry_path,
            "cad_manifest_path": file_container.cad_manifest_path,
            "cad_document_path": file_container.cad_document_path,
            "cad_metadata_path": file_container.cad_metadata_path,
            "cad_bom_path": file_container.cad_bom_path,
        }
    )
    if system_path:
        start = time.perf_counter()
        try:
            diagnostics["storage_exists"] = file_service.file_exists(system_path)
        except Exception:
            diagnostics["storage_exists"] = None
        finally:
            diagnostics["storage_head_latency_ms"] = int(
                (time.perf_counter() - start) * 1000
            )
    if payload.get("error"):
        diagnostics["error"] = payload.get("error")
    elif job.last_error:
        diagnostics["last_error"] = job.last_error
    return diagnostics


def _to_job_response(job: ConversionJob, diagnostics: Optional[Dict[str, Any]] = None) -> JobResponse:
    return JobResponse(
        id=job.id,
        task_type=job.task_type,
        payload=_sanitize_payload(job.payload or {}),
        status=job.status,
        priority=job.priority,
        worker_id=job.worker_id,
        attempt_count=job.attempt_count or 0,
        max_attempts=job.max_attempts or 0,
        last_error=job.last_error,
        dedupe_key=job.dedupe_key,
        created_at=job.created_at,
        scheduled_at=job.scheduled_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_by_id=job.created_by_id,
        diagnostics=diagnostics,
    )


@router.post("", response_model=JobResponse)
def create_job(
    req: CreateJobRequest,
    response: Response,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> JobResponse:
    ctx = get_request_context()
    tenant_id = ctx.tenant_id
    if tenant_id:
        quota_service = QuotaService(identity_db, meta_db=db)
        decisions = quota_service.evaluate(tenant_id, deltas={"active_jobs": 1})
        if decisions:
            if quota_service.mode == "soft":
                response.headers["X-Quota-Warning"] = QuotaService.build_warning(decisions)
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

    service = JobService(db)
    try:
        job = service.create_job(
            task_type=req.task_type,
            payload=req.payload,
            user_id=user_id,
            priority=req.priority,
            max_attempts=req.max_attempts,
            dedupe_key=req.dedupe_key,
            dedupe=req.dedupe,
        )
    except QuotaExceededError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc
    return _to_job_response(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    diagnostics = _build_job_diagnostics(job, db)
    return _to_job_response(job, diagnostics=diagnostics)


@router.get("", response_model=Dict[str, Any])
def list_jobs(
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    file_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(ConversionJob)
    if status:
        q = q.filter(ConversionJob.status == status)
    if task_type:
        q = q.filter(ConversionJob.task_type == task_type)
    if file_id:
        q = q.filter(_json_text(ConversionJob.payload["file_id"]) == str(file_id))

    total = q.count()
    jobs: List[ConversionJob] = (
        q.order_by(ConversionJob.created_at.desc()).offset(offset).limit(limit).all()
    )
    return {"total": total, "items": [_to_job_response(j).model_dump() for j in jobs]}
