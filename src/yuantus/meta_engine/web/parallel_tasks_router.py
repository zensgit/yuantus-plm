from __future__ import annotations

from datetime import datetime, timezone
import io
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.parallel_tasks_service import (
    BreakageIncidentService,
    ConsumptionPlanService,
    DocumentMultiSiteService,
    ECOActivityValidationService,
    ParallelOpsOverviewService,
    ThreeDOverlayService,
    WorkflowCustomActionService,
    WorkorderDocumentPackService,
)

parallel_tasks_router = APIRouter(tags=["ParallelTasks"])


def _as_roles(user: CurrentUser) -> List[str]:
    return [str(role) for role in (getattr(user, "roles", []) or [])]


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


def _manifest_to_pdf_bytes(manifest: Dict[str, Any]) -> bytes:
    def esc(text: str) -> str:
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

    export_meta = manifest.get("export_meta") if isinstance(manifest, dict) else {}
    if not isinstance(export_meta, dict):
        export_meta = {}
    scope_summary = manifest.get("scope_summary") if isinstance(manifest, dict) else {}
    if not isinstance(scope_summary, dict):
        scope_summary = {}

    lines = [
        "Workorder Document Pack",
        "=== Export Metadata ===",
        f"routing_id: {manifest.get('routing_id') or ''}",
        f"operation_id: {manifest.get('operation_id') or ''}",
        f"job_no: {export_meta.get('job_no') or ''}",
        f"operator_id: {export_meta.get('operator_id') or ''}",
        f"operator_name: {export_meta.get('operator_name') or ''}",
        f"exported_by: {export_meta.get('exported_by') or ''}",
        f"generated_at: {manifest.get('generated_at') or ''}",
        "=== Document Summary ===",
        f"total_documents: {manifest.get('count') or 0}",
        f"routing_scope_docs: {scope_summary.get('routing') or 0}",
        f"operation_scope_docs: {scope_summary.get('operation') or 0}",
        "=== Documents ===",
    ]
    for idx, row in enumerate(manifest.get("documents") or [], start=1):
        lines.append(
            f"{idx}. doc={row.get('document_item_id')} "
            f"op={row.get('operation_id') or '-'} "
            f"scope={row.get('document_scope') or '-'} "
            f"inherit={row.get('inherit_to_children')} "
            f"visible={row.get('visible_in_production')}"
        )

    y = 800
    text_ops: List[str] = []
    for line in lines:
        text_ops.append(f"1 0 0 1 40 {y} Tm ({esc(line)}) Tj")
        y -= 14
        if y < 40:
            break

    stream = "BT\n/F1 10 Tf\n" + "\n".join(text_ops) + "\nET\n"
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n"
            b"endobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        (
            f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
            + stream_bytes
            + b"endstream\nendobj\n"
        ),
    ]

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("latin-1")

    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode("latin-1")
    return pdf


# ---------------------------
# P0-A Document Multi-Site
# ---------------------------


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


@parallel_tasks_router.post("/doc-sync/sites")
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


@parallel_tasks_router.get("/doc-sync/sites")
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


@parallel_tasks_router.post("/doc-sync/sites/{site_id}/health")
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


@parallel_tasks_router.post("/doc-sync/jobs")
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


@parallel_tasks_router.get("/doc-sync/jobs")
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


@parallel_tasks_router.get("/doc-sync/jobs/{job_id}")
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


@parallel_tasks_router.post("/doc-sync/jobs/{job_id}/replay")
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


# ---------------------------
# P0-B ECO Activity Validation
# ---------------------------


class ECOActivityCreateRequest(BaseModel):
    eco_id: str
    name: str
    depends_on_activity_ids: Optional[List[str]] = None
    is_blocking: bool = True
    assignee_id: Optional[int] = None
    properties: Optional[Dict[str, Any]] = None


class ECOActivityTransitionRequest(BaseModel):
    to_status: str
    reason: Optional[str] = None


@parallel_tasks_router.post("/eco-activities")
async def create_eco_activity(
    payload: ECOActivityCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    try:
        activity = service.create_activity(
            eco_id=payload.eco_id,
            name=payload.name,
            depends_on_activity_ids=payload.depends_on_activity_ids,
            is_blocking=payload.is_blocking,
            assignee_id=payload.assignee_id,
            properties=payload.properties,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": activity.id,
        "eco_id": activity.eco_id,
        "name": activity.name,
        "status": activity.status,
        "is_blocking": bool(activity.is_blocking),
        "depends_on_activity_ids": activity.depends_on_activity_ids or [],
        "operator_id": int(user.id),
    }


@parallel_tasks_router.get("/eco-activities/{eco_id}")
async def list_eco_activities(
    eco_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    activities = service.list_activities(eco_id)
    return {
        "eco_id": eco_id,
        "total": len(activities),
        "activities": [
            {
                "id": activity.id,
                "name": activity.name,
                "status": activity.status,
                "is_blocking": bool(activity.is_blocking),
                "depends_on_activity_ids": activity.depends_on_activity_ids or [],
                "assignee_id": activity.assignee_id,
                "closed_at": activity.closed_at.isoformat() if activity.closed_at else None,
                "updated_at": activity.updated_at.isoformat() if activity.updated_at else None,
            }
            for activity in activities
        ],
        "operator_id": int(user.id),
    }


@parallel_tasks_router.post("/eco-activities/activity/{activity_id}/transition")
async def transition_eco_activity(
    activity_id: str,
    payload: ECOActivityTransitionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    try:
        activity = service.transition_activity(
            activity_id=activity_id,
            to_status=payload.to_status,
            user_id=int(user.id),
            reason=payload.reason,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message) from exc
        if "blocking dependencies" in message.lower():
            raise HTTPException(status_code=409, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc
    return {
        "id": activity.id,
        "eco_id": activity.eco_id,
        "status": activity.status,
        "closed_at": activity.closed_at.isoformat() if activity.closed_at else None,
        "operator_id": int(user.id),
    }


@parallel_tasks_router.get("/eco-activities/{eco_id}/blockers")
async def get_eco_blockers(
    eco_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    result = service.blockers_for_eco(eco_id)
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.get("/eco-activities/{eco_id}/events")
async def get_eco_activity_events(
    eco_id: str,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    events = service.recent_events(eco_id, limit=limit)
    return {
        "eco_id": eco_id,
        "total": len(events),
        "events": [
            {
                "id": event.id,
                "activity_id": event.activity_id,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "reason": event.reason,
                "user_id": event.user_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
        "operator_id": int(user.id),
    }


# ---------------------------
# P0-C Workflow Custom Actions
# ---------------------------


class WorkflowActionRuleRequest(BaseModel):
    name: str
    target_object: str = "ECO"
    workflow_map_id: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    trigger_phase: str = "before"
    action_type: str
    action_params: Optional[Dict[str, Any]] = None
    fail_strategy: str = "block"
    is_enabled: bool = True


class WorkflowActionExecuteRequest(BaseModel):
    object_id: str
    target_object: str = "ECO"
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    trigger_phase: str = "before"
    context: Optional[Dict[str, Any]] = None


@parallel_tasks_router.post("/workflow-actions/rules")
async def upsert_workflow_action_rule(
    payload: WorkflowActionRuleRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkflowCustomActionService(db)
    try:
        rule = service.create_rule(
            name=payload.name,
            target_object=payload.target_object,
            workflow_map_id=payload.workflow_map_id,
            from_state=payload.from_state,
            to_state=payload.to_state,
            trigger_phase=payload.trigger_phase,
            action_type=payload.action_type,
            action_params=payload.action_params,
            fail_strategy=payload.fail_strategy,
            is_enabled=payload.is_enabled,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="invalid_workflow_rule",
            message=str(exc),
            context={
                "name": payload.name,
                "trigger_phase": payload.trigger_phase,
                "action_type": payload.action_type,
            },
        )
    params = rule.action_params if isinstance(rule.action_params, dict) else {}
    conflict_scope = params.get("conflict_scope")
    if not isinstance(conflict_scope, dict):
        conflict_scope = {}
    return {
        "id": rule.id,
        "name": rule.name,
        "target_object": rule.target_object,
        "from_state": rule.from_state,
        "to_state": rule.to_state,
        "trigger_phase": rule.trigger_phase,
        "action_type": rule.action_type,
        "fail_strategy": rule.fail_strategy,
        "execution_priority": int(params.get("priority") or 100),
        "timeout_s": float(params.get("timeout_s") or 5.0),
        "max_retries": int(params.get("max_retries") or 0),
        "conflict_count": int(conflict_scope.get("count") or 0),
        "is_enabled": bool(rule.is_enabled),
        "operator_id": int(user.id),
    }


@parallel_tasks_router.get("/workflow-actions/rules")
async def list_workflow_action_rules(
    target_object: Optional[str] = Query(None),
    enabled_only: bool = Query(True),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkflowCustomActionService(db)
    rules = service.list_rules(target_object=target_object, enabled_only=enabled_only)
    rows = []
    for rule in rules:
        params = rule.action_params if isinstance(rule.action_params, dict) else {}
        conflict_scope = params.get("conflict_scope")
        if not isinstance(conflict_scope, dict):
            conflict_scope = {}
        rows.append(
            {
                "id": rule.id,
                "name": rule.name,
                "target_object": rule.target_object,
                "workflow_map_id": rule.workflow_map_id,
                "from_state": rule.from_state,
                "to_state": rule.to_state,
                "trigger_phase": rule.trigger_phase,
                "action_type": rule.action_type,
                "action_params": params,
                "fail_strategy": rule.fail_strategy,
                "execution_priority": int(params.get("priority") or 100),
                "timeout_s": float(params.get("timeout_s") or 5.0),
                "max_retries": int(params.get("max_retries") or 0),
                "conflict_count": int(conflict_scope.get("count") or 0),
                "is_enabled": bool(rule.is_enabled),
            }
        )
    return {
        "total": len(rules),
        "rules": rows,
        "operator_id": int(user.id),
    }


@parallel_tasks_router.post("/workflow-actions/execute")
async def execute_workflow_actions(
    payload: WorkflowActionExecuteRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkflowCustomActionService(db)
    try:
        runs = service.evaluate_transition(
            object_id=payload.object_id,
            target_object=payload.target_object,
            from_state=payload.from_state,
            to_state=payload.to_state,
            trigger_phase=payload.trigger_phase,
            context=payload.context,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="workflow_action_execution_failed",
            message=str(exc),
            context={
                "object_id": payload.object_id,
                "target_object": payload.target_object,
                "trigger_phase": payload.trigger_phase,
            },
        )
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="workflow_action_execution_failed",
            message=str(exc),
            context={
                "object_id": payload.object_id,
                "target_object": payload.target_object,
                "trigger_phase": payload.trigger_phase,
            },
        )
    return {
        "total": len(runs),
        "runs": [
            {
                "id": run.id,
                "rule_id": run.rule_id,
                "status": run.status,
                "result_code": (
                    ((run.result or {}).get("result_code"))
                    if isinstance(run.result, dict)
                    else None
                ),
                "attempts": int(run.attempts or 0),
                "last_error": run.last_error,
                "result": run.result or {},
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
            for run in runs
        ],
        "operator_id": int(user.id),
    }


# ---------------------------
# P1-E Consumption Plans
# ---------------------------


class ConsumptionPlanCreateRequest(BaseModel):
    name: str
    planned_quantity: float = Field(..., gt=0)
    uom: str = "EA"
    period_unit: str = "week"
    item_id: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class ConsumptionActualRequest(BaseModel):
    actual_quantity: float = Field(..., gt=0)
    source_type: str = "workorder"
    source_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class ConsumptionTemplateVersionCreateRequest(BaseModel):
    name: str
    planned_quantity: float = Field(..., gt=0)
    version_label: Optional[str] = None
    uom: str = "EA"
    period_unit: str = "week"
    item_id: Optional[str] = None
    activate: bool = True
    properties: Optional[Dict[str, Any]] = None


class ConsumptionTemplateVersionStateRequest(BaseModel):
    activate: bool = True


class ConsumptionTemplateImpactPreviewRequest(BaseModel):
    planned_quantity: float = Field(..., gt=0)
    uom: Optional[str] = None
    period_unit: Optional[str] = None


@parallel_tasks_router.post("/consumption/plans")
async def create_consumption_plan(
    payload: ConsumptionPlanCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    try:
        plan = service.create_plan(
            name=payload.name,
            planned_quantity=payload.planned_quantity,
            uom=payload.uom,
            period_unit=payload.period_unit,
            item_id=payload.item_id,
            created_by_id=int(user.id),
            properties=payload.properties,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": plan.id,
        "name": plan.name,
        "planned_quantity": plan.planned_quantity,
        "uom": plan.uom,
        "period_unit": plan.period_unit,
        "state": plan.state,
        "item_id": plan.item_id,
    }


@parallel_tasks_router.get("/consumption/plans")
async def list_consumption_plans(
    state: Optional[str] = Query(None),
    item_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    plans = service.list_plans(state=state, item_id=item_id)
    return {
        "total": len(plans),
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "state": plan.state,
                "planned_quantity": float(plan.planned_quantity or 0.0),
                "uom": plan.uom,
                "period_unit": plan.period_unit,
                "item_id": plan.item_id,
            }
            for plan in plans
        ],
        "operator_id": int(user.id),
    }


@parallel_tasks_router.post("/consumption/templates/{template_key}/versions")
async def create_consumption_template_version(
    template_key: str,
    payload: ConsumptionTemplateVersionCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    try:
        plan = service.create_template_version(
            template_key=template_key,
            name=payload.name,
            planned_quantity=payload.planned_quantity,
            version_label=payload.version_label,
            uom=payload.uom,
            period_unit=payload.period_unit,
            item_id=payload.item_id,
            activate=payload.activate,
            created_by_id=int(user.id),
            properties=payload.properties,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="consumption_template_version_invalid",
            message=str(exc),
            context={"template_key": template_key},
        )
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="consumption_template_version_invalid",
            message=str(exc),
            context={"template_key": template_key},
        )

    template = (plan.properties or {}).get("template") if isinstance(plan.properties, dict) else {}
    if not isinstance(template, dict):
        template = {}
    return {
        "id": plan.id,
        "name": plan.name,
        "state": plan.state,
        "planned_quantity": float(plan.planned_quantity or 0.0),
        "uom": plan.uom,
        "period_unit": plan.period_unit,
        "item_id": plan.item_id,
        "template": {
            "key": template.get("key"),
            "version": template.get("version"),
            "is_template_version": bool(template.get("is_template_version")),
            "is_active": bool(template.get("is_active")),
        },
        "operator_id": int(user.id),
    }


@parallel_tasks_router.get("/consumption/templates/{template_key}/versions")
async def list_consumption_template_versions(
    template_key: str,
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    versions = service.list_template_versions(
        template_key=template_key,
        include_inactive=include_inactive,
    )
    return {
        "template_key": template_key,
        "total": len(versions),
        "versions": versions,
        "operator_id": int(user.id),
    }


@parallel_tasks_router.post("/consumption/templates/versions/{plan_id}/state")
async def set_consumption_template_version_state(
    plan_id: str,
    payload: ConsumptionTemplateVersionStateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    try:
        plan = service.set_template_version_state(
            plan_id=plan_id,
            activate=payload.activate,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        lowered = message.lower()
        if "not found" in lowered:
            _raise_api_error(
                status_code=404,
                code="consumption_template_version_not_found",
                message=message,
                context={"plan_id": plan_id},
            )
        _raise_api_error(
            status_code=400,
            code="consumption_template_version_invalid",
            message=message,
            context={"plan_id": plan_id},
        )
    except Exception as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="consumption_template_version_invalid",
            message=str(exc),
            context={"plan_id": plan_id},
        )

    template = (plan.properties or {}).get("template") if isinstance(plan.properties, dict) else {}
    if not isinstance(template, dict):
        template = {}
    return {
        "id": plan.id,
        "state": plan.state,
        "template": {
            "key": template.get("key"),
            "version": template.get("version"),
            "is_template_version": bool(template.get("is_template_version")),
            "is_active": bool(template.get("is_active")),
        },
        "operator_id": int(user.id),
    }


@parallel_tasks_router.post("/consumption/templates/{template_key}/impact-preview")
async def preview_consumption_template_impact(
    template_key: str,
    payload: ConsumptionTemplateImpactPreviewRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    try:
        result = service.preview_template_impact(
            template_key=template_key,
            planned_quantity=payload.planned_quantity,
            uom=payload.uom,
            period_unit=payload.period_unit,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="consumption_template_preview_invalid",
            message=str(exc),
            context={"template_key": template_key},
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.post("/consumption/plans/{plan_id}/actuals")
async def add_consumption_actual(
    plan_id: str,
    payload: ConsumptionActualRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    try:
        record = service.add_actual(
            plan_id=plan_id,
            actual_quantity=payload.actual_quantity,
            source_type=payload.source_type,
            source_id=payload.source_id,
            properties=payload.properties,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": record.id,
        "plan_id": record.plan_id,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "actual_quantity": record.actual_quantity,
        "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
    }


@parallel_tasks_router.get("/consumption/plans/{plan_id}/variance")
async def get_consumption_variance(
    plan_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    try:
        result = service.variance(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.get("/consumption/dashboard")
async def get_consumption_dashboard(
    item_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConsumptionPlanService(db)
    result = service.dashboard(item_id=item_id)
    result["operator_id"] = int(user.id)
    return result


# ---------------------------
# P1-F Breakage + Metrics
# ---------------------------


class BreakageCreateRequest(BaseModel):
    description: str = Field(..., min_length=1)
    severity: str = "medium"
    status: str = "open"
    product_item_id: Optional[str] = None
    bom_line_item_id: Optional[str] = None
    production_order_id: Optional[str] = None
    version_id: Optional[str] = None
    batch_code: Optional[str] = None
    customer_name: Optional[str] = None
    responsibility: Optional[str] = None


class BreakageStatusUpdateRequest(BaseModel):
    status: str


class BreakageHelpdeskSyncRequest(BaseModel):
    metadata_json: Optional[Dict[str, Any]] = None


@parallel_tasks_router.get("/breakages/metrics")
async def get_breakage_metrics(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    product_item_id: Optional[str] = Query(None),
    batch_code: Optional[str] = Query(None),
    responsibility: Optional[str] = Query(None),
    trend_window_days: int = Query(14, description="7|14|30"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BreakageIncidentService(db)
    try:
        result = service.metrics(
            status=status,
            severity=severity,
            product_item_id=product_item_id,
            batch_code=batch_code,
            responsibility=responsibility,
            trend_window_days=trend_window_days,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="breakage_metrics_invalid_request",
            message=str(exc),
            context={
                "status": status,
                "severity": severity,
                "product_item_id": product_item_id,
                "batch_code": batch_code,
                "responsibility": responsibility,
                "trend_window_days": trend_window_days,
                "page": page,
                "page_size": page_size,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.post("/breakages")
async def create_breakage_incident(
    payload: BreakageCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BreakageIncidentService(db)
    try:
        incident = service.create_incident(
            description=payload.description,
            severity=payload.severity,
            status=payload.status,
            product_item_id=payload.product_item_id,
            bom_line_item_id=payload.bom_line_item_id,
            production_order_id=payload.production_order_id,
            version_id=payload.version_id,
            batch_code=payload.batch_code,
            customer_name=payload.customer_name,
            responsibility=payload.responsibility,
            created_by_id=int(user.id),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": incident.id,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "product_item_id": incident.product_item_id,
        "bom_line_item_id": incident.bom_line_item_id,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


@parallel_tasks_router.get("/breakages")
async def list_breakage_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    product_item_id: Optional[str] = Query(None),
    batch_code: Optional[str] = Query(None),
    responsibility: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BreakageIncidentService(db)
    incidents = service.list_incidents(
        status=status,
        severity=severity,
        product_item_id=product_item_id,
        batch_code=batch_code,
        responsibility=responsibility,
    )
    return {
        "total": len(incidents),
        "incidents": [
            {
                "id": incident.id,
                "description": incident.description,
                "severity": incident.severity,
                "status": incident.status,
                "product_item_id": incident.product_item_id,
                "bom_line_item_id": incident.bom_line_item_id,
                "production_order_id": incident.production_order_id,
                "version_id": incident.version_id,
                "batch_code": incident.batch_code,
                "customer_name": incident.customer_name,
                "responsibility": incident.responsibility,
                "created_at": (
                    incident.created_at.isoformat() if incident.created_at else None
                ),
                "updated_at": (
                    incident.updated_at.isoformat() if incident.updated_at else None
                ),
            }
            for incident in incidents
        ],
        "operator_id": int(user.id),
    }


@parallel_tasks_router.post("/breakages/{incident_id}/status")
async def update_breakage_status(
    incident_id: str,
    payload: BreakageStatusUpdateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BreakageIncidentService(db)
    try:
        incident = service.update_status(incident_id, status=payload.status)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": incident.id,
        "status": incident.status,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
        "operator_id": int(user.id),
    }


@parallel_tasks_router.post("/breakages/{incident_id}/helpdesk-sync")
async def sync_breakage_to_helpdesk_stub(
    incident_id: str,
    payload: BreakageHelpdeskSyncRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BreakageIncidentService(db)
    try:
        job = service.enqueue_helpdesk_stub_sync(
            incident_id,
            user_id=int(user.id),
            metadata_json=payload.metadata_json,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "incident_id": incident_id,
        "job_id": job.id,
        "task_type": job.task_type,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


# ---------------------------
# P2-G Workorder Document Pack
# ---------------------------


class WorkorderDocLinkRequest(BaseModel):
    routing_id: str
    operation_id: Optional[str] = None
    document_item_id: str
    inherit_to_children: bool = True
    visible_in_production: bool = True


@parallel_tasks_router.post("/workorder-docs/links")
async def upsert_workorder_doc_link(
    payload: WorkorderDocLinkRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkorderDocumentPackService(db)
    try:
        link = service.upsert_link(
            routing_id=payload.routing_id,
            operation_id=payload.operation_id,
            document_item_id=payload.document_item_id,
            inherit_to_children=payload.inherit_to_children,
            visible_in_production=payload.visible_in_production,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": link.id,
        "routing_id": link.routing_id,
        "operation_id": link.operation_id,
        "document_item_id": link.document_item_id,
        "inherit_to_children": bool(link.inherit_to_children),
        "visible_in_production": bool(link.visible_in_production),
    }


@parallel_tasks_router.get("/workorder-docs/links")
async def list_workorder_doc_links(
    routing_id: str = Query(...),
    operation_id: Optional[str] = Query(None),
    include_inherited: bool = Query(True),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkorderDocumentPackService(db)
    links = service.list_links(
        routing_id=routing_id,
        operation_id=operation_id,
        include_inherited=include_inherited,
    )
    return {
        "routing_id": routing_id,
        "operation_id": operation_id,
        "total": len(links),
        "links": [
            {
                "id": link.id,
                "routing_id": link.routing_id,
                "operation_id": link.operation_id,
                "document_item_id": link.document_item_id,
                "inherit_to_children": bool(link.inherit_to_children),
                "visible_in_production": bool(link.visible_in_production),
                "created_at": link.created_at.isoformat() if link.created_at else None,
            }
            for link in links
        ],
        "operator_id": int(user.id),
    }


@parallel_tasks_router.get("/workorder-docs/export")
async def export_workorder_doc_pack(
    routing_id: str = Query(...),
    operation_id: Optional[str] = Query(None),
    include_inherited: bool = Query(True),
    export_format: str = Query("zip", description="zip|json|pdf"),
    job_no: Optional[str] = Query(None),
    operator_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkorderDocumentPackService(db)
    result = service.export_pack(
        routing_id=routing_id,
        operation_id=operation_id,
        include_inherited=include_inherited,
        export_meta={
            "job_no": job_no,
            "operator_id": int(user.id),
            "operator_name": operator_name,
            "exported_by": str(getattr(user, "email", "") or getattr(user, "id", "")),
        },
    )
    manifest = result["manifest"]
    normalized = (export_format or "zip").strip().lower()
    if normalized == "json":
        content = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="workorder-doc-pack.json"'
            },
        )
    if normalized == "pdf":
        content = _manifest_to_pdf_bytes(manifest)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="workorder-doc-pack.pdf"'
            },
        )
    if normalized != "zip":
        _raise_api_error(
            status_code=400,
            code="workorder_export_invalid_format",
            message="export_format must be zip, json or pdf",
            context={"export_format": export_format},
        )
    return StreamingResponse(
        io.BytesIO(result["zip_bytes"]),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="workorder-doc-pack.zip"'},
    )


# ---------------------------
# P2-H 3D Metadata Overlay
# ---------------------------


class ThreeDOverlayUpsertRequest(BaseModel):
    document_item_id: str
    version_label: Optional[str] = None
    status: Optional[str] = None
    visibility_role: Optional[str] = None
    part_refs: Optional[List[Dict[str, Any]]] = None
    properties: Optional[Dict[str, Any]] = None


class ThreeDOverlayBatchResolveRequest(BaseModel):
    component_refs: List[str] = Field(..., min_length=1)
    include_missing: bool = True


@parallel_tasks_router.post("/cad-3d/overlays")
async def upsert_3d_overlay(
    payload: ThreeDOverlayUpsertRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ThreeDOverlayService(db)
    try:
        overlay = service.upsert_overlay(
            document_item_id=payload.document_item_id,
            version_label=payload.version_label,
            status=payload.status,
            visibility_role=payload.visibility_role,
            part_refs=payload.part_refs,
            properties=payload.properties,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": overlay.id,
        "document_item_id": overlay.document_item_id,
        "version_label": overlay.version_label,
        "status": overlay.status,
        "visibility_role": overlay.visibility_role,
        "part_refs_count": len(overlay.part_refs or []),
    }


@parallel_tasks_router.get("/cad-3d/overlays/cache/stats")
async def get_3d_overlay_cache_stats(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ThreeDOverlayService(db)
    result = service.cache_stats()
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.get("/cad-3d/overlays/{document_item_id}")
async def get_3d_overlay(
    document_item_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ThreeDOverlayService(db)
    try:
        overlay = service.get_overlay(
            document_item_id=document_item_id, user_roles=_as_roles(user)
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not overlay:
        raise HTTPException(status_code=404, detail=f"Overlay not found: {document_item_id}")
    return {
        "id": overlay.id,
        "document_item_id": overlay.document_item_id,
        "version_label": overlay.version_label,
        "status": overlay.status,
        "visibility_role": overlay.visibility_role,
        "part_refs": overlay.part_refs or [],
        "properties": overlay.properties or {},
    }


@parallel_tasks_router.post("/cad-3d/overlays/{document_item_id}/components/resolve-batch")
async def resolve_overlay_components_batch(
    document_item_id: str,
    payload: ThreeDOverlayBatchResolveRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ThreeDOverlayService(db)
    try:
        result = service.resolve_components(
            document_item_id=document_item_id,
            component_refs=payload.component_refs,
            user_roles=_as_roles(user),
            include_missing=payload.include_missing,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.get("/cad-3d/overlays/{document_item_id}/components/{component_ref}")
async def resolve_overlay_component(
    document_item_id: str,
    component_ref: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ThreeDOverlayService(db)
    try:
        result = service.resolve_component(
            document_item_id=document_item_id,
            component_ref=component_ref,
            user_roles=_as_roles(user),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


# ---------------------------
# P3-I Parallel Ops Overview
# ---------------------------


@parallel_tasks_router.get("/parallel-ops/summary")
async def get_parallel_ops_summary(
    window_days: int = Query(7, description="1|7|14|30|90"),
    site_id: Optional[str] = Query(None),
    target_object: Optional[str] = Query(None),
    template_key: Optional[str] = Query(None),
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
            },
        )
    result["operator_id"] = int(user.id)
    return result
