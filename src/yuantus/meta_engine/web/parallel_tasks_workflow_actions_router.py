from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.parallel_tasks_service import (
    WorkflowCustomActionService,
)

parallel_tasks_workflow_actions_router = APIRouter(tags=["ParallelTasks"])


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


@parallel_tasks_workflow_actions_router.post("/workflow-actions/rules")
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


@parallel_tasks_workflow_actions_router.get("/workflow-actions/rules")
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


@parallel_tasks_workflow_actions_router.post("/workflow-actions/execute")
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
