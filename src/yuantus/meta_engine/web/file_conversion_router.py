from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.job import ConversionJob as MetaConversionJob
from yuantus.meta_engine.models.job import JobStatus
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.services.job_worker import JobWorker


file_conversion_router = APIRouter(prefix="/file", tags=["File Management"])

VAULT_DIR = get_settings().LOCAL_STORAGE_PATH

_PREVIEW_FORMATS = {"png", "jpg", "jpeg"}
_FILE_CONVERSION_TASK_TYPES = ("cad_conversion", "cad_preview", "cad_geometry")
_LEGACY_CONVERSION_SUNSET = "Wed, 31 Dec 2026 00:00:00 GMT"


class ConversionJobResponse(BaseModel):
    """Conversion job status response."""

    id: str
    source_file_id: str
    target_format: str
    operation_type: str
    status: str
    error_message: Optional[str] = None
    result_file_id: Optional[str] = None


class FileConversionJobStatus(BaseModel):
    id: str
    source: str
    task_type: str
    target_format: Optional[str] = None
    operation_type: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    result_file_id: Optional[str] = None


class FileConversionJobsSummary(BaseModel):
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    total: int = 0


class FileConversionSummaryResponse(BaseModel):
    file_id: str
    filename: str
    conversion_status: Optional[str] = None
    conversion_jobs: List[FileConversionJobStatus] = Field(default_factory=list)
    conversion_jobs_summary: FileConversionJobsSummary
    viewer_readiness: Dict[str, Any] = Field(default_factory=dict)


def _meta_job_result_file_id(job: MetaConversionJob) -> Optional[str]:
    if str(job.status or "").lower() != "completed":
        return None
    payload = job.payload if isinstance(job.payload, dict) else {}
    result = payload.get("result")
    if isinstance(result, dict):
        file_id = result.get("file_id")
        if file_id:
            return str(file_id)
    file_id = payload.get("file_id")
    return str(file_id) if file_id else None


def _meta_job_target_format(job: MetaConversionJob) -> str:
    payload = job.payload if isinstance(job.payload, dict) else {}
    if job.task_type == "cad_preview":
        return "png"
    if job.task_type == "cad_geometry":
        return str(payload.get("target_format") or "gltf")
    return str(payload.get("target_format") or "")


def _meta_job_operation_type(job: MetaConversionJob) -> str:
    if job.task_type == "cad_preview":
        return "preview"
    return "convert"


def _meta_job_to_response(job: MetaConversionJob) -> ConversionJobResponse:
    payload = job.payload if isinstance(job.payload, dict) else {}
    return ConversionJobResponse(
        id=job.id,
        source_file_id=str(payload.get("file_id") or ""),
        target_format=_meta_job_target_format(job),
        operation_type=_meta_job_operation_type(job),
        status=job.status,
        error_message=job.last_error,
        result_file_id=_meta_job_result_file_id(job),
    )


def _request_context_user_id() -> Optional[int]:
    ctx = get_request_context()
    if not ctx.user_id:
        return None
    try:
        return int(ctx.user_id)
    except (TypeError, ValueError):
        return None


def _build_conversion_job_payload(
    file_container: FileContainer, target_format: str
) -> Dict[str, Any]:
    ctx = get_request_context()
    payload: Dict[str, Any] = {
        "file_id": file_container.id,
        "filename": file_container.filename,
    }
    if file_container.cad_format:
        payload["cad_format"] = file_container.cad_format
    if target_format not in _PREVIEW_FORMATS:
        payload["target_format"] = target_format
    if ctx.tenant_id:
        payload["tenant_id"] = ctx.tenant_id
    if ctx.org_id:
        payload["org_id"] = ctx.org_id
    if ctx.user_id:
        payload["user_id"] = ctx.user_id
    return payload


def _queue_file_conversion_job(
    db: Session,
    file_container: FileContainer,
    target_format: str,
    *,
    priority: int = 10,
) -> MetaConversionJob:
    normalized = str(target_format or "").strip().lower() or "obj"
    task_type = "cad_preview" if normalized in _PREVIEW_FORMATS else "cad_geometry"
    payload = _build_conversion_job_payload(file_container, normalized)
    job_service = JobService(db)
    return job_service.create_job(
        task_type,
        payload,
        user_id=_request_context_user_id(),
        priority=priority,
    )


def _build_conversion_job_worker(worker_id: str) -> JobWorker:
    from yuantus.meta_engine.tasks.cad_conversion_tasks import perform_cad_conversion
    from yuantus.meta_engine.tasks.cad_pipeline_tasks import (
        cad_geometry_with_binding,
        cad_preview_with_binding,
    )

    worker = JobWorker(worker_id=worker_id, poll_interval=0)
    worker.register_handler("cad_conversion", perform_cad_conversion)
    worker.register_handler("cad_preview", cad_preview_with_binding)
    worker.register_handler("cad_geometry", cad_geometry_with_binding)
    return worker


def _set_legacy_conversion_headers(response: Response, file_id: str) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _LEGACY_CONVERSION_SUNSET
    response.headers["Link"] = (
        f'</api/v1/file/{file_id}/convert>; rel="successor-version"'
    )


def _collect_meta_conversion_jobs(
    db: Session, file_id: str, limit: int = 100
) -> List[MetaConversionJob]:
    jobs = (
        db.query(MetaConversionJob)
        .order_by(MetaConversionJob.created_at.desc())
        .limit(limit)
        .all()
    )
    filtered: List[MetaConversionJob] = []
    for job in jobs:
        payload = job.payload if isinstance(job.payload, dict) else {}
        if str(payload.get("file_id") or "") != file_id:
            continue
        if str(job.task_type or "") not in _FILE_CONVERSION_TASK_TYPES:
            continue
        filtered.append(job)
    return filtered


def _summarize_file_conversion_jobs(
    jobs: List[FileConversionJobStatus],
) -> FileConversionJobsSummary:
    summary = FileConversionJobsSummary()
    for job in jobs:
        status = str(job.status or "").lower()
        if status == "pending":
            summary.pending += 1
        elif status == "processing":
            summary.processing += 1
        elif status == "completed":
            summary.completed += 1
        elif status == "failed":
            summary.failed += 1
    summary.total = len(jobs)
    return summary


@file_conversion_router.get("/supported-formats", deprecated=True)
async def get_supported_formats(db: Session = Depends(get_db)):
    """Get list of supported file formats and conversion capabilities."""
    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    return converter.get_supported_conversions()


@file_conversion_router.get(
    "/{file_id}/conversion_summary", response_model=FileConversionSummaryResponse
)
async def get_file_conversion_summary(file_id: str, db: Session = Depends(get_db)):
    """Canonical file-level conversion summary across the meta job queue."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    viewer_readiness = converter.assess_viewer_readiness(file_container)

    meta_jobs = _collect_meta_conversion_jobs(db, file_id)

    jobs: List[FileConversionJobStatus] = []
    jobs.extend(
        [
            FileConversionJobStatus(
                id=job.id,
                source="meta",
                task_type=job.task_type,
                target_format=_meta_job_target_format(job),
                operation_type=_meta_job_operation_type(job),
                status=job.status,
                error_message=job.last_error,
                result_file_id=_meta_job_result_file_id(job),
            )
            for job in meta_jobs
        ]
    )

    return FileConversionSummaryResponse(
        file_id=file_container.id,
        filename=file_container.filename,
        conversion_status=file_container.conversion_status,
        conversion_jobs=jobs,
        conversion_jobs_summary=_summarize_file_conversion_jobs(jobs),
        viewer_readiness=viewer_readiness,
    )


@file_conversion_router.post("/{file_id}/convert", response_model=ConversionJobResponse)
async def request_conversion(
    file_id: str,
    target_format: str = Query("obj", description="Target format (obj, gltf, stl)"),
    db: Session = Depends(get_db),
):
    """
    Request CAD file conversion to viewable format.

    Creates a conversion job in the queue.
    """
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_container.is_cad_file():
        raise HTTPException(status_code=400, detail="File is not a CAD file")

    try:
        job = _queue_file_conversion_job(db, file_container, target_format)
        return _meta_job_to_response(job)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@file_conversion_router.get("/conversion/{job_id}", response_model=ConversionJobResponse)
async def get_conversion_status(job_id: str, db: Session = Depends(get_db)):
    """Get status of a conversion job."""
    meta_job = db.get(MetaConversionJob, job_id)
    if meta_job and str(meta_job.task_type or "") in _FILE_CONVERSION_TASK_TYPES:
        return _meta_job_to_response(meta_job)

    raise HTTPException(status_code=404, detail="Conversion job not found")


@file_conversion_router.get("/conversions/pending")
async def list_pending_conversions(
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
):
    """List pending conversion jobs from the canonical meta queue."""
    meta_jobs = (
        db.query(MetaConversionJob)
        .filter(
            MetaConversionJob.status.in_(
                [
                    JobStatus.PENDING.value,
                    JobStatus.PROCESSING.value,
                ]
            ),
            MetaConversionJob.task_type.in_(list(_FILE_CONVERSION_TASK_TYPES)),
        )
        .order_by(MetaConversionJob.priority.asc(), MetaConversionJob.created_at.asc())
        .limit(limit)
        .all()
    )
    return [_meta_job_to_response(job) for job in meta_jobs]


@file_conversion_router.post("/conversions/process")
async def process_conversion_queue(
    batch_size: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """
    Process pending conversion jobs.

    This endpoint is typically called by a background worker.
    """
    try:
        job_service = JobService(db)
        job_service.requeue_stale_jobs()
        worker = _build_conversion_job_worker("file-router-conversions")
        results = {"processed": 0, "succeeded": 0, "failed": 0}
        for _ in range(batch_size):
            job = job_service.poll_next_job(
                worker.worker_id,
                task_types=list(_FILE_CONVERSION_TASK_TYPES),
            )
            if not job:
                break
            results["processed"] += 1
            worker._execute_job(job, job_service)
            db.refresh(job)
            if job.status == JobStatus.COMPLETED.value:
                results["succeeded"] += 1
            elif job.status == JobStatus.FAILED.value:
                results["failed"] += 1
        return results

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@file_conversion_router.post("/process_cad")
async def process_cad_legacy(
    payload: dict, response: Response, db: Session = Depends(get_db)
):
    """
    Legacy endpoint for triggering CAD conversion.
    Prefer using POST /{file_id}/convert instead.
    """
    file_id = payload.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing file_id")

    target_format = str(payload.get("target_format", "obj") or "obj").strip().lower()
    _set_legacy_conversion_headers(response, str(file_id))

    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(
            status_code=404,
            detail=(
                "Input file not found. Use POST /api/v1/file/{file_id}/convert "
                "with an existing FileContainer."
            ),
        )
    if not file_container.is_cad_file():
        raise HTTPException(status_code=400, detail="File is not a CAD file")

    try:
        job = _queue_file_conversion_job(db, file_container, target_format)
        return {
            "status": "queued",
            "job_id": job.id,
            "status_url": f"/api/v1/file/conversion/{job.id}",
            "viewable_url": (
                f"/api/v1/file/{file_id}/preview"
                if target_format in _PREVIEW_FORMATS
                else f"/api/v1/file/{file_id}/geometry"
            ),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
