"""Generic approval ops / summary API endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.approvals.service import ApprovalService

approval_ops_router = APIRouter(prefix="/approvals", tags=["Approvals"])


def _export_response(
    *,
    payload: Dict[str, Any] | str,
    fmt: str,
    stem: str,
):
    if fmt == "json":
        return JSONResponse(
            content=payload,
            headers={"content-disposition": f'attachment; filename="{stem}.json"'},
        )
    if fmt == "csv":
        if not isinstance(payload, str):
            raise HTTPException(
                status_code=500,
                detail="Export response for csv requires string payload",
            )
        return PlainTextResponse(
            content=str(payload),
            media_type="text/csv; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{stem}.csv"'},
        )
    if fmt == "markdown":
        if not isinstance(payload, str):
            raise HTTPException(
                status_code=500,
                detail="Export response for markdown requires string payload",
            )
        return PlainTextResponse(
            content=str(payload),
            media_type="text/markdown; charset=utf-8",
            headers={"content-disposition": f'attachment; filename="{stem}.md"'},
        )
    raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")


def _normalize_export_format(fmt: str) -> str:
    normalized = (fmt or "").strip().lower()
    if normalized not in {"json", "csv", "markdown"}:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")
    return normalized


@approval_ops_router.get("/summary")
async def approval_summary(
    entity_type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    return svc.get_summary(entity_type=entity_type, category_id=category_id)


@approval_ops_router.get("/summary/export")
async def export_approval_summary(
    format: str = Query("json"),
    entity_type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    normalized_format = _normalize_export_format(format)
    svc = ApprovalService(db)
    try:
        payload = svc.export_summary(
            fmt=normalized_format,
            entity_type=entity_type,
            category_id=category_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _export_response(
        payload=payload,
        fmt=normalized_format,
        stem="approval-summary-export",
    )


@approval_ops_router.get("/ops-report")
async def approvals_ops_report(db: Session = Depends(get_db)):
    svc = ApprovalService(db)
    return svc.get_ops_report()


@approval_ops_router.get("/ops-report/export")
async def export_approvals_ops_report(
    format: str = Query("json"),
    db: Session = Depends(get_db),
):
    normalized_format = _normalize_export_format(format)
    svc = ApprovalService(db)
    try:
        payload = svc.export_ops_report(fmt=normalized_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _export_response(payload=payload, fmt=normalized_format, stem="approval-ops-report")


@approval_ops_router.get("/queue-health")
async def approvals_queue_health(
    stale_after_hours: int = Query(24, ge=1, le=168),
    warn_after_hours: int = Query(4, ge=1, le=168),
    entity_type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    try:
        return svc.get_queue_health(
            stale_after_hours=stale_after_hours,
            warn_after_hours=warn_after_hours,
            entity_type=entity_type,
            category_id=category_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@approval_ops_router.get("/queue-health/export")
async def export_approvals_queue_health(
    format: str = Query("json"),
    stale_after_hours: int = Query(24, ge=1, le=168),
    warn_after_hours: int = Query(4, ge=1, le=168),
    entity_type: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    normalized_format = _normalize_export_format(format)
    svc = ApprovalService(db)
    try:
        payload = svc.export_queue_health(
            fmt=normalized_format,
            stale_after_hours=stale_after_hours,
            warn_after_hours=warn_after_hours,
            entity_type=entity_type,
            category_id=category_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _export_response(
        payload=payload,
        fmt=normalized_format,
        stem="approval-queue-health",
    )
