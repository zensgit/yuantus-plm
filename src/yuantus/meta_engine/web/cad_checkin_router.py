from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.exceptions.handlers import QuotaExceededError
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.checkin_service import CheckinManager
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.quota_service import QuotaService

cad_checkin_router = APIRouter(prefix="/cad", tags=["CAD"])


def get_checkin_manager(
    user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> CheckinManager:
    # RBACUser should have an integer ID map?
    # user.id is the key (99, 1, 2)
    return CheckinManager(db, user_id=user.id)


def _build_checkin_status_url(request: Request, item_id: str) -> str:
    return str(request.url_for("get_cad_checkin_status", item_id=item_id))


def _build_file_status_url(request: Request, file_id: str) -> str:
    return str(request.url_for("get_file_conversion_summary", file_id=file_id))


class CadCheckinResponse(BaseModel):
    status: str
    item_id: str
    version_id: str
    generation: int
    file_id: Optional[str] = None
    conversion_job_ids: List[str] = Field(default_factory=list)
    status_url: str
    file_status_url: Optional[str] = None


class CadCheckinJobStatus(BaseModel):
    id: str
    task_type: str
    status: str


class CadCheckinJobsSummary(BaseModel):
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    total: int = 0


class CadCheckinStatusResponse(BaseModel):
    item_id: str
    version_id: str
    file_id: str
    filename: Optional[str] = None
    conversion_job_ids: List[str] = Field(default_factory=list)
    conversion_jobs: List[CadCheckinJobStatus] = Field(default_factory=list)
    conversion_jobs_summary: CadCheckinJobsSummary
    viewer_readiness: Dict[str, Any] = Field(default_factory=dict)
    file_status_url: Optional[str] = None


def _summarize_jobs(jobs: List[ConversionJob]) -> CadCheckinJobsSummary:
    summary = CadCheckinJobsSummary()
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


def _get_checkin_jobs(
    db: Session,
    *,
    item_id: str,
    version_id: str,
    file_id: str,
    anchored_job_ids: Optional[List[str]] = None,
) -> List[ConversionJob]:
    anchored_job_ids = [jid for jid in (anchored_job_ids or []) if jid]
    query = db.query(ConversionJob)
    if anchored_job_ids:
        jobs = (
            query.filter(ConversionJob.id.in_(anchored_job_ids))
            .order_by(ConversionJob.created_at.desc())
            .all()
        )
        ordered = {job.id: job for job in jobs}
        return [ordered[jid] for jid in anchored_job_ids if jid in ordered]

    candidates = query.order_by(ConversionJob.created_at.desc()).limit(100).all()
    filtered: List[ConversionJob] = []
    for job in candidates:
        payload = job.payload or {}
        if str(payload.get("item_id") or "") != item_id:
            continue
        if str(payload.get("version_id") or "") != version_id:
            continue
        if str(payload.get("file_id") or "") != file_id:
            continue
        if job.task_type not in {"cad_preview", "cad_geometry"}:
            continue
        filtered.append(job)
    return filtered


@cad_checkin_router.post("/{item_id}/checkout")
def checkout_document(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    """
    Lock a document for editing.
    """
    try:
        item = mgr.checkout(item_id)
        # Commit handled by service or need manual commit?
        # Service flushes, but typically Router/Dependencies commit.
        # But CheckinManager commits/flushes?
        # CheckinManager.checkout does 'add' and 'flush'.
        # We need final commit.
        mgr.session.commit()
        return {
            "status": "success",
            "message": "Item locked.",
            "locked_by_id": item.locked_by_id,
        }
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        mgr.session.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@cad_checkin_router.post("/{item_id}/undo-checkout")
def undo_checkout(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    try:
        mgr.undo_checkout(item_id)
        mgr.session.commit()
        return {"status": "success", "message": "Item unlocked."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@cad_checkin_router.post("/{item_id}/checkin")
def checkin_document(
    item_id: str,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    mgr: CheckinManager = Depends(get_checkin_manager),
    user: CurrentUser = Depends(get_current_user),
    identity_db: Session = Depends(get_identity_db),
) -> CadCheckinResponse:
    """
    Upload new file version and unlock.
    """
    try:
        content = file.file.read()
        filename = file.filename

        quota_service = QuotaService(identity_db, meta_db=mgr.session)
        decisions = quota_service.evaluate(
            user.tenant_id, deltas={"files": 1, "storage_bytes": len(content)}
        )
        if decisions:
            if quota_service.mode == "soft":
                response.headers["X-Quota-Warning"] = QuotaService.build_warning(decisions)
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(user.tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

        new_item = mgr.checkin(item_id, content, filename)
        mgr.session.commit()

        props = new_item.properties or {}
        file_id = props.get("native_file")
        job_ids = [
            str(job_id)
            for job_id in (props.get("cad_conversion_job_ids") or [])
            if job_id
        ]

        return CadCheckinResponse(
            status="success",
            item_id=item_id,
            version_id=new_item.id,
            generation=new_item.generation,
            file_id=file_id,
            conversion_job_ids=job_ids,
            status_url=_build_checkin_status_url(request, item_id),
            file_status_url=_build_file_status_url(request, file_id) if file_id else None,
        )
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        mgr.session.rollback()
        raise
    except Exception as e:
        mgr.session.rollback()
        # Log error
        raise HTTPException(status_code=500, detail=str(e)) from e


@cad_checkin_router.get("/{item_id}/checkin-status", response_model=CadCheckinStatusResponse)
def get_cad_checkin_status(
    item_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadCheckinStatusResponse:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.current_version_id:
        raise HTTPException(status_code=404, detail="Current version missing")

    version = db.get(ItemVersion, item.current_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Current version not found")

    props = version.properties or {}
    native_file_id = str(props.get("native_file") or "").strip()
    if not native_file_id:
        raise HTTPException(status_code=404, detail="Native CAD file missing")

    native_file = db.get(FileContainer, native_file_id)
    if not native_file:
        raise HTTPException(status_code=404, detail="Native CAD file not found")

    anchored_job_ids = [
        str(job_id)
        for job_id in (props.get("cad_conversion_job_ids") or [])
        if job_id
    ]
    jobs = _get_checkin_jobs(
        db,
        item_id=item_id,
        version_id=version.id,
        file_id=native_file_id,
        anchored_job_ids=anchored_job_ids,
    )
    summary = _summarize_jobs(jobs)
    viewer_readiness = CADConverterService(
        db, vault_base_path=get_settings().LOCAL_STORAGE_PATH
    ).assess_viewer_readiness(native_file)

    return CadCheckinStatusResponse(
        item_id=item_id,
        version_id=version.id,
        file_id=native_file.id,
        filename=native_file.filename,
        conversion_job_ids=anchored_job_ids or [job.id for job in jobs],
        conversion_jobs=[
            CadCheckinJobStatus(
                id=job.id,
                task_type=job.task_type,
                status=job.status,
            )
            for job in jobs
        ],
        conversion_jobs_summary=summary,
        viewer_readiness=viewer_readiness,
        file_status_url=_build_file_status_url(request, native_file.id),
    )
