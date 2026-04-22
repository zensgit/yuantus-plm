from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.parallel_tasks_service import ParallelOpsOverviewService


parallel_tasks_ops_router = APIRouter(tags=["ParallelTasks"])


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


# ---------------------------
# P3-I Parallel Ops Overview
# ---------------------------


class ParallelOpsBreakageHelpdeskFailuresExportJobCreateRequest(BaseModel):
    window_days: int = Field(7, ge=1, le=90)
    provider: Optional[str] = None
    failure_category: Optional[str] = None
    provider_ticket_status: Optional[str] = None
    export_format: str = Field("json", description="json|csv|md|zip")
    execute_immediately: bool = True


class ParallelOpsBreakageHelpdeskFailuresExportCleanupRequest(BaseModel):
    ttl_hours: int = Field(24, ge=1, le=720)
    limit: int = Field(200, ge=1, le=1000)


class ParallelOpsBreakageHelpdeskFailureTriageApplyRequest(BaseModel):
    triage_status: str = Field(..., min_length=1)
    job_ids: Optional[List[str]] = None
    window_days: int = Field(7, ge=1, le=90)
    provider: Optional[str] = None
    failure_category: Optional[str] = None
    provider_ticket_status: Optional[str] = None
    limit: int = Field(100, ge=1, le=500)
    triage_owner: Optional[str] = None
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[List[str]] = None


class ParallelOpsBreakageHelpdeskFailureReplayRequest(BaseModel):
    job_ids: Optional[List[str]] = None
    window_days: int = Field(7, ge=1, le=90)
    provider: Optional[str] = None
    failure_category: Optional[str] = None
    provider_ticket_status: Optional[str] = None
    limit: int = Field(100, ge=1, le=500)


class ParallelOpsBreakageHelpdeskFailureReplayCleanupRequest(BaseModel):
    ttl_hours: int = Field(168, ge=1, le=720)
    limit: int = Field(200, ge=1, le=1000)
    dry_run: bool = False


@parallel_tasks_ops_router.get("/parallel-ops/summary")
async def get_parallel_ops_summary(
    window_days: int = Query(7, description="1|7|14|30|90"),
    site_id: Optional[str] = Query(None),
    target_object: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
    overlay_cache_hit_rate_warn: Optional[float] = Query(None),
    overlay_cache_min_requests_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_rate_warn: Optional[float] = Query(None),
    workflow_failed_rate_warn: Optional[float] = Query(None),
    breakage_open_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_triage_coverage_warn: Optional[float] = Query(None),
    breakage_helpdesk_export_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_critical: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_critical: Optional[int] = Query(None),
    breakage_helpdesk_replay_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_replay_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_replay_pending_total_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_block_on_dead_letter_only: Optional[bool] = Query(None),
    doc_sync_checkout_gate_max_pending_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_processing_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_failed_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_dead_letter_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_trend_delta_warn: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.summary(
            window_days=window_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            overlay_cache_hit_rate_warn=overlay_cache_hit_rate_warn,
            overlay_cache_min_requests_warn=overlay_cache_min_requests_warn,
            doc_sync_dead_letter_rate_warn=doc_sync_dead_letter_rate_warn,
            workflow_failed_rate_warn=workflow_failed_rate_warn,
            breakage_open_rate_warn=breakage_open_rate_warn,
            breakage_helpdesk_failed_rate_warn=breakage_helpdesk_failed_rate_warn,
            breakage_helpdesk_failed_total_warn=breakage_helpdesk_failed_total_warn,
            breakage_helpdesk_triage_coverage_warn=breakage_helpdesk_triage_coverage_warn,
            breakage_helpdesk_export_failed_total_warn=breakage_helpdesk_export_failed_total_warn,
            breakage_helpdesk_provider_failed_rate_warn=breakage_helpdesk_provider_failed_rate_warn,
            breakage_helpdesk_provider_failed_min_jobs_warn=breakage_helpdesk_provider_failed_min_jobs_warn,
            breakage_helpdesk_provider_failed_rate_critical=breakage_helpdesk_provider_failed_rate_critical,
            breakage_helpdesk_provider_failed_min_jobs_critical=breakage_helpdesk_provider_failed_min_jobs_critical,
            breakage_helpdesk_replay_failed_rate_warn=breakage_helpdesk_replay_failed_rate_warn,
            breakage_helpdesk_replay_failed_total_warn=breakage_helpdesk_replay_failed_total_warn,
            breakage_helpdesk_replay_pending_total_warn=breakage_helpdesk_replay_pending_total_warn,
            doc_sync_checkout_gate_block_on_dead_letter_only=doc_sync_checkout_gate_block_on_dead_letter_only,
            doc_sync_checkout_gate_max_pending_warn=doc_sync_checkout_gate_max_pending_warn,
            doc_sync_checkout_gate_max_processing_warn=doc_sync_checkout_gate_max_processing_warn,
            doc_sync_checkout_gate_max_failed_warn=doc_sync_checkout_gate_max_failed_warn,
            doc_sync_checkout_gate_max_dead_letter_warn=doc_sync_checkout_gate_max_dead_letter_warn,
            doc_sync_dead_letter_trend_delta_warn=doc_sync_dead_letter_trend_delta_warn,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
                "overlay_cache_hit_rate_warn": overlay_cache_hit_rate_warn,
                "overlay_cache_min_requests_warn": overlay_cache_min_requests_warn,
                "doc_sync_dead_letter_rate_warn": doc_sync_dead_letter_rate_warn,
                "workflow_failed_rate_warn": workflow_failed_rate_warn,
                "breakage_open_rate_warn": breakage_open_rate_warn,
                "breakage_helpdesk_failed_rate_warn": breakage_helpdesk_failed_rate_warn,
                "breakage_helpdesk_failed_total_warn": breakage_helpdesk_failed_total_warn,
                "breakage_helpdesk_triage_coverage_warn": breakage_helpdesk_triage_coverage_warn,
                "breakage_helpdesk_export_failed_total_warn": breakage_helpdesk_export_failed_total_warn,
                "breakage_helpdesk_provider_failed_rate_warn": breakage_helpdesk_provider_failed_rate_warn,
                "breakage_helpdesk_provider_failed_min_jobs_warn": breakage_helpdesk_provider_failed_min_jobs_warn,
                "breakage_helpdesk_provider_failed_rate_critical": breakage_helpdesk_provider_failed_rate_critical,
                "breakage_helpdesk_provider_failed_min_jobs_critical": breakage_helpdesk_provider_failed_min_jobs_critical,
                "breakage_helpdesk_replay_failed_rate_warn": breakage_helpdesk_replay_failed_rate_warn,
                "breakage_helpdesk_replay_failed_total_warn": breakage_helpdesk_replay_failed_total_warn,
                "breakage_helpdesk_replay_pending_total_warn": breakage_helpdesk_replay_pending_total_warn,
                "doc_sync_checkout_gate_block_on_dead_letter_only": doc_sync_checkout_gate_block_on_dead_letter_only,
                "doc_sync_checkout_gate_max_pending_warn": doc_sync_checkout_gate_max_pending_warn,
                "doc_sync_checkout_gate_max_processing_warn": doc_sync_checkout_gate_max_processing_warn,
                "doc_sync_checkout_gate_max_failed_warn": doc_sync_checkout_gate_max_failed_warn,
                "doc_sync_checkout_gate_max_dead_letter_warn": doc_sync_checkout_gate_max_dead_letter_warn,
                "doc_sync_dead_letter_trend_delta_warn": doc_sync_dead_letter_trend_delta_warn,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/trends")
async def get_parallel_ops_trends(
    window_days: int = Query(7, description="1|7|14|30|90"),
    bucket_days: int = Query(1, description="1|7|14|30"),
    site_id: Optional[str] = Query(None),
    target_object: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.trends(
            window_days=window_days,
            bucket_days=bucket_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "bucket_days": bucket_days,
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/alerts")
async def get_parallel_ops_alerts(
    window_days: int = Query(7, description="1|7|14|30|90"),
    site_id: Optional[str] = Query(None),
    target_object: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
    level: Optional[str] = Query(None, description="warn|critical|info"),
    overlay_cache_hit_rate_warn: Optional[float] = Query(None),
    overlay_cache_min_requests_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_rate_warn: Optional[float] = Query(None),
    workflow_failed_rate_warn: Optional[float] = Query(None),
    breakage_open_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_triage_coverage_warn: Optional[float] = Query(None),
    breakage_helpdesk_export_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_critical: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_critical: Optional[int] = Query(None),
    breakage_helpdesk_replay_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_replay_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_replay_pending_total_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_block_on_dead_letter_only: Optional[bool] = Query(None),
    doc_sync_checkout_gate_max_pending_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_processing_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_failed_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_dead_letter_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_trend_delta_warn: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.alerts(
            window_days=window_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            level=level,
            overlay_cache_hit_rate_warn=overlay_cache_hit_rate_warn,
            overlay_cache_min_requests_warn=overlay_cache_min_requests_warn,
            doc_sync_dead_letter_rate_warn=doc_sync_dead_letter_rate_warn,
            workflow_failed_rate_warn=workflow_failed_rate_warn,
            breakage_open_rate_warn=breakage_open_rate_warn,
            breakage_helpdesk_failed_rate_warn=breakage_helpdesk_failed_rate_warn,
            breakage_helpdesk_failed_total_warn=breakage_helpdesk_failed_total_warn,
            breakage_helpdesk_triage_coverage_warn=breakage_helpdesk_triage_coverage_warn,
            breakage_helpdesk_export_failed_total_warn=breakage_helpdesk_export_failed_total_warn,
            breakage_helpdesk_provider_failed_rate_warn=breakage_helpdesk_provider_failed_rate_warn,
            breakage_helpdesk_provider_failed_min_jobs_warn=breakage_helpdesk_provider_failed_min_jobs_warn,
            breakage_helpdesk_provider_failed_rate_critical=breakage_helpdesk_provider_failed_rate_critical,
            breakage_helpdesk_provider_failed_min_jobs_critical=breakage_helpdesk_provider_failed_min_jobs_critical,
            breakage_helpdesk_replay_failed_rate_warn=breakage_helpdesk_replay_failed_rate_warn,
            breakage_helpdesk_replay_failed_total_warn=breakage_helpdesk_replay_failed_total_warn,
            breakage_helpdesk_replay_pending_total_warn=breakage_helpdesk_replay_pending_total_warn,
            doc_sync_checkout_gate_block_on_dead_letter_only=doc_sync_checkout_gate_block_on_dead_letter_only,
            doc_sync_checkout_gate_max_pending_warn=doc_sync_checkout_gate_max_pending_warn,
            doc_sync_checkout_gate_max_processing_warn=doc_sync_checkout_gate_max_processing_warn,
            doc_sync_checkout_gate_max_failed_warn=doc_sync_checkout_gate_max_failed_warn,
            doc_sync_checkout_gate_max_dead_letter_warn=doc_sync_checkout_gate_max_dead_letter_warn,
            doc_sync_dead_letter_trend_delta_warn=doc_sync_dead_letter_trend_delta_warn,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
                "level": level,
                "overlay_cache_hit_rate_warn": overlay_cache_hit_rate_warn,
                "overlay_cache_min_requests_warn": overlay_cache_min_requests_warn,
                "doc_sync_dead_letter_rate_warn": doc_sync_dead_letter_rate_warn,
                "workflow_failed_rate_warn": workflow_failed_rate_warn,
                "breakage_open_rate_warn": breakage_open_rate_warn,
                "breakage_helpdesk_failed_rate_warn": breakage_helpdesk_failed_rate_warn,
                "breakage_helpdesk_failed_total_warn": breakage_helpdesk_failed_total_warn,
                "breakage_helpdesk_triage_coverage_warn": breakage_helpdesk_triage_coverage_warn,
                "breakage_helpdesk_export_failed_total_warn": breakage_helpdesk_export_failed_total_warn,
                "breakage_helpdesk_provider_failed_rate_warn": breakage_helpdesk_provider_failed_rate_warn,
                "breakage_helpdesk_provider_failed_min_jobs_warn": breakage_helpdesk_provider_failed_min_jobs_warn,
                "breakage_helpdesk_provider_failed_rate_critical": breakage_helpdesk_provider_failed_rate_critical,
                "breakage_helpdesk_provider_failed_min_jobs_critical": breakage_helpdesk_provider_failed_min_jobs_critical,
                "breakage_helpdesk_replay_failed_rate_warn": breakage_helpdesk_replay_failed_rate_warn,
                "breakage_helpdesk_replay_failed_total_warn": breakage_helpdesk_replay_failed_total_warn,
                "breakage_helpdesk_replay_pending_total_warn": breakage_helpdesk_replay_pending_total_warn,
                "doc_sync_checkout_gate_block_on_dead_letter_only": doc_sync_checkout_gate_block_on_dead_letter_only,
                "doc_sync_checkout_gate_max_pending_warn": doc_sync_checkout_gate_max_pending_warn,
                "doc_sync_checkout_gate_max_processing_warn": doc_sync_checkout_gate_max_processing_warn,
                "doc_sync_checkout_gate_max_failed_warn": doc_sync_checkout_gate_max_failed_warn,
                "doc_sync_checkout_gate_max_dead_letter_warn": doc_sync_checkout_gate_max_dead_letter_warn,
                "doc_sync_dead_letter_trend_delta_warn": doc_sync_dead_letter_trend_delta_warn,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/summary/export")
async def export_parallel_ops_summary(
    window_days: int = Query(7, description="1|7|14|30|90"),
    site_id: Optional[str] = Query(None),
    target_object: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
    export_format: str = Query("json", description="json|csv|md"),
    report_lang: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
    locale_profile_id: Optional[str] = Query(None),
    overlay_cache_hit_rate_warn: Optional[float] = Query(None),
    overlay_cache_min_requests_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_rate_warn: Optional[float] = Query(None),
    workflow_failed_rate_warn: Optional[float] = Query(None),
    breakage_open_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_triage_coverage_warn: Optional[float] = Query(None),
    breakage_helpdesk_export_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_critical: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_critical: Optional[int] = Query(None),
    breakage_helpdesk_replay_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_replay_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_replay_pending_total_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_block_on_dead_letter_only: Optional[bool] = Query(None),
    doc_sync_checkout_gate_max_pending_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_processing_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_failed_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_dead_letter_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_trend_delta_warn: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        exported = service.export_summary(
            window_days=window_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            export_format=export_format,
            report_lang=report_lang,
            report_type=report_type,
            locale_profile_id=locale_profile_id,
            overlay_cache_hit_rate_warn=overlay_cache_hit_rate_warn,
            overlay_cache_min_requests_warn=overlay_cache_min_requests_warn,
            doc_sync_dead_letter_rate_warn=doc_sync_dead_letter_rate_warn,
            workflow_failed_rate_warn=workflow_failed_rate_warn,
            breakage_open_rate_warn=breakage_open_rate_warn,
            breakage_helpdesk_failed_rate_warn=breakage_helpdesk_failed_rate_warn,
            breakage_helpdesk_failed_total_warn=breakage_helpdesk_failed_total_warn,
            breakage_helpdesk_triage_coverage_warn=breakage_helpdesk_triage_coverage_warn,
            breakage_helpdesk_export_failed_total_warn=breakage_helpdesk_export_failed_total_warn,
            breakage_helpdesk_provider_failed_rate_warn=breakage_helpdesk_provider_failed_rate_warn,
            breakage_helpdesk_provider_failed_min_jobs_warn=breakage_helpdesk_provider_failed_min_jobs_warn,
            breakage_helpdesk_provider_failed_rate_critical=breakage_helpdesk_provider_failed_rate_critical,
            breakage_helpdesk_provider_failed_min_jobs_critical=breakage_helpdesk_provider_failed_min_jobs_critical,
            breakage_helpdesk_replay_failed_rate_warn=breakage_helpdesk_replay_failed_rate_warn,
            breakage_helpdesk_replay_failed_total_warn=breakage_helpdesk_replay_failed_total_warn,
            breakage_helpdesk_replay_pending_total_warn=breakage_helpdesk_replay_pending_total_warn,
            doc_sync_checkout_gate_block_on_dead_letter_only=doc_sync_checkout_gate_block_on_dead_letter_only,
            doc_sync_checkout_gate_max_pending_warn=doc_sync_checkout_gate_max_pending_warn,
            doc_sync_checkout_gate_max_processing_warn=doc_sync_checkout_gate_max_processing_warn,
            doc_sync_checkout_gate_max_failed_warn=doc_sync_checkout_gate_max_failed_warn,
            doc_sync_checkout_gate_max_dead_letter_warn=doc_sync_checkout_gate_max_dead_letter_warn,
            doc_sync_dead_letter_trend_delta_warn=doc_sync_dead_letter_trend_delta_warn,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
                "export_format": export_format,
                "report_lang": report_lang,
                "report_type": report_type,
                "locale_profile_id": locale_profile_id,
                "overlay_cache_hit_rate_warn": overlay_cache_hit_rate_warn,
                "overlay_cache_min_requests_warn": overlay_cache_min_requests_warn,
                "doc_sync_dead_letter_rate_warn": doc_sync_dead_letter_rate_warn,
                "workflow_failed_rate_warn": workflow_failed_rate_warn,
                "breakage_open_rate_warn": breakage_open_rate_warn,
                "breakage_helpdesk_failed_rate_warn": breakage_helpdesk_failed_rate_warn,
                "breakage_helpdesk_failed_total_warn": breakage_helpdesk_failed_total_warn,
                "breakage_helpdesk_triage_coverage_warn": breakage_helpdesk_triage_coverage_warn,
                "breakage_helpdesk_export_failed_total_warn": breakage_helpdesk_export_failed_total_warn,
                "breakage_helpdesk_provider_failed_rate_warn": breakage_helpdesk_provider_failed_rate_warn,
                "breakage_helpdesk_provider_failed_min_jobs_warn": breakage_helpdesk_provider_failed_min_jobs_warn,
                "breakage_helpdesk_provider_failed_rate_critical": breakage_helpdesk_provider_failed_rate_critical,
                "breakage_helpdesk_provider_failed_min_jobs_critical": breakage_helpdesk_provider_failed_min_jobs_critical,
                "breakage_helpdesk_replay_failed_rate_warn": breakage_helpdesk_replay_failed_rate_warn,
                "breakage_helpdesk_replay_failed_total_warn": breakage_helpdesk_replay_failed_total_warn,
                "breakage_helpdesk_replay_pending_total_warn": breakage_helpdesk_replay_pending_total_warn,
                "doc_sync_checkout_gate_block_on_dead_letter_only": doc_sync_checkout_gate_block_on_dead_letter_only,
                "doc_sync_checkout_gate_max_pending_warn": doc_sync_checkout_gate_max_pending_warn,
                "doc_sync_checkout_gate_max_processing_warn": doc_sync_checkout_gate_max_processing_warn,
                "doc_sync_checkout_gate_max_failed_warn": doc_sync_checkout_gate_max_failed_warn,
                "doc_sync_checkout_gate_max_dead_letter_warn": doc_sync_checkout_gate_max_dead_letter_warn,
                "doc_sync_dead_letter_trend_delta_warn": doc_sync_dead_letter_trend_delta_warn,
            },
        )
    return StreamingResponse(
        io.BytesIO(exported.get("content") or b""),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "parallel-ops-summary.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


@parallel_tasks_ops_router.get("/parallel-ops/trends/export")
async def export_parallel_ops_trends(
    window_days: int = Query(7, description="1|7|14|30|90"),
    bucket_days: int = Query(1, description="1|7|14|30"),
    site_id: Optional[str] = Query(None),
    target_object: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
    export_format: str = Query("json", description="json|csv|md"),
    report_lang: Optional[str] = Query(None),
    report_type: Optional[str] = Query(None),
    locale_profile_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        exported = service.export_trends(
            window_days=window_days,
            bucket_days=bucket_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            export_format=export_format,
            report_lang=report_lang,
            report_type=report_type,
            locale_profile_id=locale_profile_id,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "bucket_days": bucket_days,
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
                "export_format": export_format,
                "report_lang": report_lang,
                "report_type": report_type,
                "locale_profile_id": locale_profile_id,
            },
        )
    return StreamingResponse(
        io.BytesIO(exported.get("content") or b""),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "parallel-ops-trends.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


@parallel_tasks_ops_router.get("/parallel-ops/doc-sync/failures")
async def get_parallel_ops_doc_sync_failures(
    window_days: int = Query(7, description="1|7|14|30|90"),
    site_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.doc_sync_failures(
            window_days=window_days,
            site_id=site_id,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "site_id": site_id,
                "page": page,
                "page_size": page_size,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/workflow/failures")
async def get_parallel_ops_workflow_failures(
    window_days: int = Query(7, description="1|7|14|30|90"),
    target_object: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.workflow_failures(
            window_days=window_days,
            target_object=target_object,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "target_object": target_object,
                "page": page,
                "page_size": page_size,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures")
async def get_parallel_ops_breakage_helpdesk_failures(
    window_days: int = Query(7, description="1|7|14|30|90"),
    provider: Optional[str] = Query(None),
    failure_category: Optional[str] = Query(None),
    provider_ticket_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.breakage_helpdesk_failures(
            window_days=window_days,
            provider=provider,
            failure_category=failure_category,
            provider_ticket_status=provider_ticket_status,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "provider": provider,
                "failure_category": failure_category,
                "provider_ticket_status": provider_ticket_status,
                "page": page,
                "page_size": page_size,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/trends")
async def get_parallel_ops_breakage_helpdesk_failure_trends(
    window_days: int = Query(7, description="1|7|14|30|90"),
    bucket_days: int = Query(1, description="1|7|14|30"),
    provider: Optional[str] = Query(None),
    failure_category: Optional[str] = Query(None),
    provider_ticket_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.breakage_helpdesk_failure_trends(
            window_days=window_days,
            bucket_days=bucket_days,
            provider=provider,
            failure_category=failure_category,
            provider_ticket_status=provider_ticket_status,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "bucket_days": bucket_days,
                "provider": provider,
                "failure_category": failure_category,
                "provider_ticket_status": provider_ticket_status,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/triage")
async def get_parallel_ops_breakage_helpdesk_failures_triage(
    window_days: int = Query(7, description="1|7|14|30|90"),
    provider: Optional[str] = Query(None),
    failure_category: Optional[str] = Query(None),
    provider_ticket_status: Optional[str] = Query(None),
    top_n: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.breakage_helpdesk_failure_triage(
            window_days=window_days,
            provider=provider,
            failure_category=failure_category,
            provider_ticket_status=provider_ticket_status,
            top_n=top_n,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "provider": provider,
                "failure_category": failure_category,
                "provider_ticket_status": provider_ticket_status,
                "top_n": top_n,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.post("/parallel-ops/breakage-helpdesk/failures/triage/apply")
async def apply_parallel_ops_breakage_helpdesk_failures_triage(
    payload: ParallelOpsBreakageHelpdeskFailureTriageApplyRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.apply_breakage_helpdesk_failure_triage(
            triage_status=payload.triage_status,
            job_ids=payload.job_ids,
            window_days=payload.window_days,
            provider=payload.provider,
            failure_category=payload.failure_category,
            provider_ticket_status=payload.provider_ticket_status,
            limit=payload.limit,
            triage_owner=payload.triage_owner,
            root_cause=payload.root_cause,
            resolution=payload.resolution,
            note=payload.note,
            tags=payload.tags,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "triage_status": payload.triage_status,
                "window_days": payload.window_days,
                "provider": payload.provider,
                "failure_category": payload.failure_category,
                "provider_ticket_status": payload.provider_ticket_status,
                "limit": payload.limit,
                "job_ids_total": len(payload.job_ids or []),
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.post("/parallel-ops/breakage-helpdesk/failures/replay/enqueue")
async def enqueue_parallel_ops_breakage_helpdesk_failures_replay(
    payload: ParallelOpsBreakageHelpdeskFailureReplayRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.enqueue_breakage_helpdesk_failure_replay_jobs(
            job_ids=payload.job_ids,
            window_days=payload.window_days,
            provider=payload.provider,
            failure_category=payload.failure_category,
            provider_ticket_status=payload.provider_ticket_status,
            limit=payload.limit,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": payload.window_days,
                "provider": payload.provider,
                "failure_category": payload.failure_category,
                "provider_ticket_status": payload.provider_ticket_status,
                "limit": payload.limit,
                "job_ids_total": len(payload.job_ids or []),
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/replay/batches")
async def list_parallel_ops_breakage_helpdesk_failures_replay_batches(
    window_days: int = Query(7, description="1|7|14|30|90"),
    provider: Optional[str] = Query(None),
    job_status: Optional[str] = Query(
        None,
        description="pending|processing|completed|failed|cancelled|unknown",
    ),
    sync_status: Optional[str] = Query(
        None,
        description="queued|pending|processing|completed|failed|cancelled|unknown",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.list_breakage_helpdesk_failure_replay_batches(
            window_days=window_days,
            provider=provider,
            job_status=job_status,
            sync_status=sync_status,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "provider": provider,
                "job_status": job_status,
                "sync_status": sync_status,
                "page": page,
                "page_size": page_size,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/replay/trends")
async def get_parallel_ops_breakage_helpdesk_failures_replay_trends(
    window_days: int = Query(7, description="1|7|14|30|90"),
    bucket_days: int = Query(1, description="1|7|14|30"),
    provider: Optional[str] = Query(None),
    job_status: Optional[str] = Query(
        None,
        description="pending|processing|completed|failed|cancelled|unknown",
    ),
    sync_status: Optional[str] = Query(
        None,
        description="queued|pending|processing|completed|failed|cancelled|unknown",
    ),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.breakage_helpdesk_replay_trends(
            window_days=window_days,
            bucket_days=bucket_days,
            provider=provider,
            job_status=job_status,
            sync_status=sync_status,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "bucket_days": bucket_days,
                "provider": provider,
                "job_status": job_status,
                "sync_status": sync_status,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/replay/trends/export")
async def export_parallel_ops_breakage_helpdesk_failures_replay_trends(
    window_days: int = Query(7, description="1|7|14|30|90"),
    bucket_days: int = Query(1, description="1|7|14|30"),
    provider: Optional[str] = Query(None),
    job_status: Optional[str] = Query(
        None,
        description="pending|processing|completed|failed|cancelled|unknown",
    ),
    sync_status: Optional[str] = Query(
        None,
        description="queued|pending|processing|completed|failed|cancelled|unknown",
    ),
    export_format: str = Query("json", description="json|csv|md"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        exported = service.export_breakage_helpdesk_replay_trends(
            window_days=window_days,
            bucket_days=bucket_days,
            provider=provider,
            job_status=job_status,
            sync_status=sync_status,
            export_format=export_format,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "bucket_days": bucket_days,
                "provider": provider,
                "job_status": job_status,
                "sync_status": sync_status,
                "export_format": export_format,
            },
        )
    return StreamingResponse(
        io.BytesIO(exported.get("content") or b""),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "parallel-ops-breakage-helpdesk-replay-trends.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


@parallel_tasks_ops_router.get(
    "/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}"
)
async def get_parallel_ops_breakage_helpdesk_failures_replay_batch(
    batch_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.get_breakage_helpdesk_failure_replay_batch(
            batch_id,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        status_code = 400
        code = "parallel_ops_invalid_request"
        if "not found" in str(exc).lower():
            status_code = 404
            code = "parallel_ops_replay_batch_not_found"
        _raise_api_error(
            status_code=status_code,
            code=code,
            message=str(exc),
            context={
                "batch_id": batch_id,
                "page": page,
                "page_size": page_size,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get(
    "/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}/export"
)
async def export_parallel_ops_breakage_helpdesk_failures_replay_batch(
    batch_id: str,
    export_format: str = Query("json", description="json|csv|md"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        exported = service.export_breakage_helpdesk_failure_replay_batch(
            batch_id,
            export_format=export_format,
        )
    except ValueError as exc:
        status_code = 400
        code = "parallel_ops_invalid_request"
        if "not found" in str(exc).lower():
            status_code = 404
            code = "parallel_ops_replay_batch_not_found"
        _raise_api_error(
            status_code=status_code,
            code=code,
            message=str(exc),
            context={"batch_id": batch_id, "export_format": export_format},
        )
    return StreamingResponse(
        io.BytesIO(exported.get("content") or b""),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "parallel-ops-breakage-helpdesk-replay-batch.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


@parallel_tasks_ops_router.post("/parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup")
async def cleanup_parallel_ops_breakage_helpdesk_failures_replay_batches(
    payload: ParallelOpsBreakageHelpdeskFailureReplayCleanupRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.cleanup_breakage_helpdesk_failure_replay_batches(
            ttl_hours=payload.ttl_hours,
            limit=payload.limit,
            dry_run=payload.dry_run,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "ttl_hours": payload.ttl_hours,
                "limit": payload.limit,
                "dry_run": payload.dry_run,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/export")
async def export_parallel_ops_breakage_helpdesk_failures(
    window_days: int = Query(7, description="1|7|14|30|90"),
    provider: Optional[str] = Query(None),
    failure_category: Optional[str] = Query(None),
    provider_ticket_status: Optional[str] = Query(None),
    export_format: str = Query("json", description="json|csv|md|zip"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        exported = service.export_breakage_helpdesk_failures(
            window_days=window_days,
            provider=provider,
            failure_category=failure_category,
            provider_ticket_status=provider_ticket_status,
            export_format=export_format,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "provider": provider,
                "failure_category": failure_category,
                "provider_ticket_status": provider_ticket_status,
                "export_format": export_format,
            },
        )
    return StreamingResponse(
        io.BytesIO(exported.get("content") or b""),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "parallel-ops-breakage-helpdesk-failures.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


@parallel_tasks_ops_router.post("/parallel-ops/breakage-helpdesk/failures/export/jobs")
async def create_parallel_ops_breakage_helpdesk_failures_export_job(
    payload: ParallelOpsBreakageHelpdeskFailuresExportJobCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.enqueue_breakage_helpdesk_failures_export_job(
            window_days=payload.window_days,
            provider=payload.provider,
            failure_category=payload.failure_category,
            provider_ticket_status=payload.provider_ticket_status,
            export_format=payload.export_format,
            execute_immediately=payload.execute_immediately,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="parallel_ops_export_job_invalid",
            message=str(exc),
            context={
                "window_days": payload.window_days,
                "provider": payload.provider,
                "failure_category": payload.failure_category,
                "provider_ticket_status": payload.provider_ticket_status,
                "export_format": payload.export_format,
                "execute_immediately": payload.execute_immediately,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.post("/parallel-ops/breakage-helpdesk/failures/export/jobs/cleanup")
async def cleanup_parallel_ops_breakage_helpdesk_failures_export_job_results(
    payload: ParallelOpsBreakageHelpdeskFailuresExportCleanupRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.cleanup_expired_breakage_helpdesk_failures_export_results(
            ttl_hours=payload.ttl_hours,
            limit=payload.limit,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="parallel_ops_export_job_invalid",
            message=str(exc),
            context={"ttl_hours": payload.ttl_hours, "limit": payload.limit},
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/export/jobs/overview")
async def get_parallel_ops_breakage_helpdesk_failures_export_jobs_overview(
    window_days: int = Query(7, description="1|7|14|30|90"),
    provider: Optional[str] = Query(None),
    failure_category: Optional[str] = Query(None),
    export_format: Optional[str] = Query(None, description="json|csv|md|zip"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.breakage_helpdesk_failures_export_jobs_overview(
            window_days=window_days,
            provider=provider,
            failure_category=failure_category,
            export_format=export_format,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "provider": provider,
                "failure_category": failure_category,
                "export_format": export_format,
                "page": page,
                "page_size": page_size,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get("/parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}")
async def get_parallel_ops_breakage_helpdesk_failures_export_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.get_breakage_helpdesk_failures_export_job(job_id)
    except ValueError as exc:
        code = "parallel_ops_export_job_not_found"
        status_code = 404
        if "not found" not in str(exc).lower():
            code = "parallel_ops_export_job_invalid"
            status_code = 400
        _raise_api_error(
            status_code=status_code,
            code=code,
            message=str(exc),
            context={"job_id": job_id},
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.post(
    "/parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}/run"
)
async def run_parallel_ops_breakage_helpdesk_failures_export_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        result = service.run_breakage_helpdesk_failures_export_job(
            job_id,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        code = "parallel_ops_export_job_not_found"
        status_code = 404
        if "not found" not in str(exc).lower():
            code = "parallel_ops_export_job_invalid"
            status_code = 400
        _raise_api_error(
            status_code=status_code,
            code=code,
            message=str(exc),
            context={"job_id": job_id},
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_ops_router.get(
    "/parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}/download"
)
async def download_parallel_ops_breakage_helpdesk_failures_export_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        exported = service.download_breakage_helpdesk_failures_export_job(job_id)
    except ValueError as exc:
        code = "parallel_ops_export_job_not_found"
        status_code = 404
        if "not found" not in str(exc).lower():
            code = "parallel_ops_export_job_invalid"
            status_code = 400
        _raise_api_error(
            status_code=status_code,
            code=code,
            message=str(exc),
            context={"job_id": job_id},
        )
    return StreamingResponse(
        io.BytesIO(exported.get("content") or b""),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "parallel-ops-breakage-helpdesk-failures.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


@parallel_tasks_ops_router.get("/parallel-ops/metrics")
async def get_parallel_ops_metrics(
    window_days: int = Query(7, description="1|7|14|30|90"),
    site_id: Optional[str] = Query(None),
    target_object: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
    overlay_cache_hit_rate_warn: Optional[float] = Query(None),
    overlay_cache_min_requests_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_rate_warn: Optional[float] = Query(None),
    workflow_failed_rate_warn: Optional[float] = Query(None),
    breakage_open_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_triage_coverage_warn: Optional[float] = Query(None),
    breakage_helpdesk_export_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_warn: Optional[int] = Query(None),
    breakage_helpdesk_provider_failed_rate_critical: Optional[float] = Query(None),
    breakage_helpdesk_provider_failed_min_jobs_critical: Optional[int] = Query(None),
    breakage_helpdesk_replay_failed_rate_warn: Optional[float] = Query(None),
    breakage_helpdesk_replay_failed_total_warn: Optional[int] = Query(None),
    breakage_helpdesk_replay_pending_total_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_block_on_dead_letter_only: Optional[bool] = Query(None),
    doc_sync_checkout_gate_max_pending_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_processing_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_failed_warn: Optional[int] = Query(None),
    doc_sync_checkout_gate_max_dead_letter_warn: Optional[int] = Query(None),
    doc_sync_dead_letter_trend_delta_warn: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ParallelOpsOverviewService(db)
    try:
        content = service.prometheus_metrics(
            window_days=window_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            overlay_cache_hit_rate_warn=overlay_cache_hit_rate_warn,
            overlay_cache_min_requests_warn=overlay_cache_min_requests_warn,
            doc_sync_dead_letter_rate_warn=doc_sync_dead_letter_rate_warn,
            workflow_failed_rate_warn=workflow_failed_rate_warn,
            breakage_open_rate_warn=breakage_open_rate_warn,
            breakage_helpdesk_failed_rate_warn=breakage_helpdesk_failed_rate_warn,
            breakage_helpdesk_failed_total_warn=breakage_helpdesk_failed_total_warn,
            breakage_helpdesk_triage_coverage_warn=breakage_helpdesk_triage_coverage_warn,
            breakage_helpdesk_export_failed_total_warn=breakage_helpdesk_export_failed_total_warn,
            breakage_helpdesk_provider_failed_rate_warn=breakage_helpdesk_provider_failed_rate_warn,
            breakage_helpdesk_provider_failed_min_jobs_warn=breakage_helpdesk_provider_failed_min_jobs_warn,
            breakage_helpdesk_provider_failed_rate_critical=breakage_helpdesk_provider_failed_rate_critical,
            breakage_helpdesk_provider_failed_min_jobs_critical=breakage_helpdesk_provider_failed_min_jobs_critical,
            breakage_helpdesk_replay_failed_rate_warn=breakage_helpdesk_replay_failed_rate_warn,
            breakage_helpdesk_replay_failed_total_warn=breakage_helpdesk_replay_failed_total_warn,
            breakage_helpdesk_replay_pending_total_warn=breakage_helpdesk_replay_pending_total_warn,
            doc_sync_checkout_gate_block_on_dead_letter_only=doc_sync_checkout_gate_block_on_dead_letter_only,
            doc_sync_checkout_gate_max_pending_warn=doc_sync_checkout_gate_max_pending_warn,
            doc_sync_checkout_gate_max_processing_warn=doc_sync_checkout_gate_max_processing_warn,
            doc_sync_checkout_gate_max_failed_warn=doc_sync_checkout_gate_max_failed_warn,
            doc_sync_checkout_gate_max_dead_letter_warn=doc_sync_checkout_gate_max_dead_letter_warn,
            doc_sync_dead_letter_trend_delta_warn=doc_sync_dead_letter_trend_delta_warn,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="parallel_ops_invalid_request",
            message=str(exc),
            context={
                "window_days": window_days,
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
                "overlay_cache_hit_rate_warn": overlay_cache_hit_rate_warn,
                "overlay_cache_min_requests_warn": overlay_cache_min_requests_warn,
                "doc_sync_dead_letter_rate_warn": doc_sync_dead_letter_rate_warn,
                "workflow_failed_rate_warn": workflow_failed_rate_warn,
                "breakage_open_rate_warn": breakage_open_rate_warn,
                "breakage_helpdesk_failed_rate_warn": breakage_helpdesk_failed_rate_warn,
                "breakage_helpdesk_failed_total_warn": breakage_helpdesk_failed_total_warn,
                "breakage_helpdesk_triage_coverage_warn": breakage_helpdesk_triage_coverage_warn,
                "breakage_helpdesk_export_failed_total_warn": breakage_helpdesk_export_failed_total_warn,
                "breakage_helpdesk_provider_failed_rate_warn": breakage_helpdesk_provider_failed_rate_warn,
                "breakage_helpdesk_provider_failed_min_jobs_warn": breakage_helpdesk_provider_failed_min_jobs_warn,
                "breakage_helpdesk_provider_failed_rate_critical": breakage_helpdesk_provider_failed_rate_critical,
                "breakage_helpdesk_provider_failed_min_jobs_critical": breakage_helpdesk_provider_failed_min_jobs_critical,
                "breakage_helpdesk_replay_failed_rate_warn": breakage_helpdesk_replay_failed_rate_warn,
                "breakage_helpdesk_replay_failed_total_warn": breakage_helpdesk_replay_failed_total_warn,
                "breakage_helpdesk_replay_pending_total_warn": breakage_helpdesk_replay_pending_total_warn,
                "doc_sync_checkout_gate_block_on_dead_letter_only": doc_sync_checkout_gate_block_on_dead_letter_only,
                "doc_sync_checkout_gate_max_pending_warn": doc_sync_checkout_gate_max_pending_warn,
                "doc_sync_checkout_gate_max_processing_warn": doc_sync_checkout_gate_max_processing_warn,
                "doc_sync_checkout_gate_max_failed_warn": doc_sync_checkout_gate_max_failed_warn,
                "doc_sync_checkout_gate_max_dead_letter_warn": doc_sync_checkout_gate_max_dead_letter_warn,
                "doc_sync_dead_letter_trend_delta_warn": doc_sync_dead_letter_trend_delta_warn,
            },
        )
    return PlainTextResponse(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers={"X-Operator-Id": str(int(user.id))},
    )
