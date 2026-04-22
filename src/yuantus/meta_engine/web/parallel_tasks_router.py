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
from yuantus.meta_engine.services.parallel_tasks_service import (
    ECOActivityValidationService,
    WorkflowCustomActionService,
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
    to_status: str = Field(
        ...,
        description=(
            "pending|active|completed|canceled|exception "
            "(aliases: draft|in_progress|eco|done|cancel)"
        ),
    )
    reason: Optional[str] = None


class ECOActivityBulkTransitionCheckRequest(BaseModel):
    to_status: str = Field(
        ...,
        description=(
            "pending|active|completed|canceled|exception "
            "(aliases: draft|in_progress|eco|done|cancel)"
        ),
    )
    activity_ids: Optional[List[str]] = None
    include_terminal: bool = False
    include_non_blocking: bool = True
    limit: int = Field(200, ge=1, le=500)


class ECOActivityBulkTransitionRequest(ECOActivityBulkTransitionCheckRequest):
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
        _raise_api_error(
            status_code=400,
            code="eco_activity_invalid_request",
            message=str(exc),
            context={
                "eco_id": payload.eco_id,
                "name": payload.name,
            },
        )
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
            _raise_api_error(
                status_code=404,
                code="eco_activity_not_found",
                message=message,
                context={"activity_id": activity_id},
            )
        if "blocking dependencies" in message.lower():
            _raise_api_error(
                status_code=409,
                code="eco_activity_blocked",
                message=message,
                context={
                    "activity_id": activity_id,
                    "to_status": payload.to_status,
                },
            )
        _raise_api_error(
            status_code=400,
            code="eco_activity_transition_invalid",
            message=message,
            context={
                "activity_id": activity_id,
                "to_status": payload.to_status,
            },
        )
    return {
        "id": activity.id,
        "eco_id": activity.eco_id,
        "status": activity.status,
        "closed_at": activity.closed_at.isoformat() if activity.closed_at else None,
        "operator_id": int(user.id),
    }


@parallel_tasks_router.get("/eco-activities/activity/{activity_id}/transition-check")
async def check_eco_activity_transition(
    activity_id: str,
    to_status: str = Query(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    try:
        result = service.evaluate_transition(
            activity_id=activity_id,
            to_status=to_status,
        )
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            _raise_api_error(
                status_code=404,
                code="eco_activity_not_found",
                message=message,
                context={"activity_id": activity_id},
            )
        _raise_api_error(
            status_code=400,
            code="eco_activity_transition_invalid",
            message=message,
            context={
                "activity_id": activity_id,
                "to_status": to_status,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.post("/eco-activities/{eco_id}/transition-check/bulk")
async def check_eco_activity_transitions_bulk(
    eco_id: str,
    payload: ECOActivityBulkTransitionCheckRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    try:
        result = service.evaluate_transitions_bulk(
            eco_id,
            to_status=payload.to_status,
            activity_ids=payload.activity_ids,
            include_terminal=payload.include_terminal,
            include_non_blocking=payload.include_non_blocking,
            limit=payload.limit,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="eco_activity_transition_invalid",
            message=str(exc),
            context={
                "eco_id": eco_id,
                "to_status": payload.to_status,
                "limit": payload.limit,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.post("/eco-activities/{eco_id}/transition/bulk")
async def transition_eco_activities_bulk(
    eco_id: str,
    payload: ECOActivityBulkTransitionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    try:
        result = service.transition_activities_bulk(
            eco_id,
            to_status=payload.to_status,
            activity_ids=payload.activity_ids,
            include_terminal=payload.include_terminal,
            include_non_blocking=payload.include_non_blocking,
            limit=payload.limit,
            user_id=int(user.id),
            reason=payload.reason,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        _raise_api_error(
            status_code=400,
            code="eco_activity_transition_invalid",
            message=str(exc),
            context={
                "eco_id": eco_id,
                "to_status": payload.to_status,
                "limit": payload.limit,
            },
        )
    result["operator_id"] = int(user.id)
    return result


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


@parallel_tasks_router.get("/eco-activities/{eco_id}/sla")
async def get_eco_activity_sla(
    eco_id: str,
    due_soon_hours: int = Query(24),
    include_closed: bool = Query(False),
    assignee_id: Optional[int] = Query(None),
    limit: int = Query(100),
    evaluated_at: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    now = _parse_utc_datetime(evaluated_at, field_name="evaluated_at")
    try:
        result = service.activity_sla(
            eco_id,
            now=now,
            due_soon_hours=due_soon_hours,
            include_closed=include_closed,
            assignee_id=assignee_id,
            limit=limit,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="eco_activity_sla_invalid",
            message=str(exc),
            context={
                "eco_id": eco_id,
                "due_soon_hours": due_soon_hours,
                "include_closed": bool(include_closed),
                "assignee_id": assignee_id,
                "limit": limit,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.get("/eco-activities/{eco_id}/sla/alerts")
async def get_eco_activity_sla_alerts(
    eco_id: str,
    due_soon_hours: int = Query(24),
    include_closed: bool = Query(False),
    assignee_id: Optional[int] = Query(None),
    limit: int = Query(100),
    evaluated_at: Optional[str] = Query(None),
    overdue_rate_warn: float = Query(0.2),
    due_soon_count_warn: int = Query(5),
    blocking_overdue_warn: int = Query(1),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    now = _parse_utc_datetime(evaluated_at, field_name="evaluated_at")
    try:
        result = service.activity_sla_alerts(
            eco_id,
            now=now,
            due_soon_hours=due_soon_hours,
            include_closed=include_closed,
            assignee_id=assignee_id,
            limit=limit,
            overdue_rate_warn=overdue_rate_warn,
            due_soon_count_warn=due_soon_count_warn,
            blocking_overdue_warn=blocking_overdue_warn,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="eco_activity_sla_alerts_invalid",
            message=str(exc),
            context={
                "eco_id": eco_id,
                "due_soon_hours": due_soon_hours,
                "include_closed": bool(include_closed),
                "assignee_id": assignee_id,
                "limit": limit,
                "overdue_rate_warn": overdue_rate_warn,
                "due_soon_count_warn": due_soon_count_warn,
                "blocking_overdue_warn": blocking_overdue_warn,
            },
        )
    result["operator_id"] = int(user.id)
    return result


@parallel_tasks_router.get("/eco-activities/{eco_id}/sla/alerts/export")
async def export_eco_activity_sla_alerts(
    eco_id: str,
    due_soon_hours: int = Query(24),
    include_closed: bool = Query(False),
    assignee_id: Optional[int] = Query(None),
    limit: int = Query(100),
    evaluated_at: Optional[str] = Query(None),
    overdue_rate_warn: float = Query(0.2),
    due_soon_count_warn: int = Query(5),
    blocking_overdue_warn: int = Query(1),
    export_format: str = Query("json", description="json|csv|md"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ECOActivityValidationService(db)
    now = _parse_utc_datetime(evaluated_at, field_name="evaluated_at")
    try:
        exported = service.export_activity_sla_alerts(
            eco_id,
            now=now,
            due_soon_hours=due_soon_hours,
            include_closed=include_closed,
            assignee_id=assignee_id,
            limit=limit,
            overdue_rate_warn=overdue_rate_warn,
            due_soon_count_warn=due_soon_count_warn,
            blocking_overdue_warn=blocking_overdue_warn,
            export_format=export_format,
        )
    except ValueError as exc:
        _raise_api_error(
            status_code=400,
            code="eco_activity_sla_alerts_export_invalid",
            message=str(exc),
            context={
                "eco_id": eco_id,
                "due_soon_hours": due_soon_hours,
                "include_closed": bool(include_closed),
                "assignee_id": assignee_id,
                "limit": limit,
                "overdue_rate_warn": overdue_rate_warn,
                "due_soon_count_warn": due_soon_count_warn,
                "blocking_overdue_warn": blocking_overdue_warn,
                "export_format": export_format,
            },
        )
    return StreamingResponse(
        io.BytesIO(exported["content"]),
        media_type=str(exported.get("media_type") or "application/octet-stream"),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exported.get("filename") or "eco-activity-sla-alerts.bin"}"'
            ),
            "X-Operator-Id": str(int(user.id)),
        },
    )


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
    match_predicates: Optional[Dict[str, Any]] = None
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
            match_predicates=payload.match_predicates,
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
    match_predicates = params.get("match_predicates")
    if not isinstance(match_predicates, dict):
        match_predicates = {}
    return {
        "id": rule.id,
        "name": rule.name,
        "target_object": rule.target_object,
        "workflow_map_id": rule.workflow_map_id,
        "from_state": rule.from_state,
        "to_state": rule.to_state,
        "trigger_phase": rule.trigger_phase,
        "action_type": rule.action_type,
        "fail_strategy": rule.fail_strategy,
        "execution_priority": int(params.get("priority") or 100),
        "timeout_s": float(params.get("timeout_s") or 5.0),
        "max_retries": int(params.get("max_retries") or 0),
        "match_predicates": match_predicates,
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
        match_predicates = params.get("match_predicates")
        if not isinstance(match_predicates, dict):
            match_predicates = {}
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
                "match_predicates": match_predicates,
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
    runtime_context = dict(payload.context or {})
    runtime_context.setdefault("actor_roles", _as_roles(user))
    try:
        runs = service.evaluate_transition(
            object_id=payload.object_id,
            target_object=payload.target_object,
            from_state=payload.from_state,
            to_state=payload.to_state,
            trigger_phase=payload.trigger_phase,
            context=runtime_context,
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
