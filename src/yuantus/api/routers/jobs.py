from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.models.job import ConversionJob
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


def _to_job_response(job: ConversionJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        task_type=job.task_type,
        payload=job.payload or {},
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
    return _to_job_response(job)


@router.get("", response_model=Dict[str, Any])
def list_jobs(
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    q = db.query(ConversionJob)
    if status:
        q = q.filter(ConversionJob.status == status)
    if task_type:
        q = q.filter(ConversionJob.task_type == task_type)

    total = q.count()
    jobs: List[ConversionJob] = (
        q.order_by(ConversionJob.created_at.desc()).offset(offset).limit(limit).all()
    )
    return {"total": total, "items": [_to_job_response(j).model_dump() for j in jobs]}
