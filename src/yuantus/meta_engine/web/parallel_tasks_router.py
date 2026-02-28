from __future__ import annotations

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
    ThreeDOverlayService,
    WorkflowCustomActionService,
    WorkorderDocumentPackService,
)

parallel_tasks_router = APIRouter(tags=["ParallelTasks"])


def _as_roles(user: CurrentUser) -> List[str]:
    return [str(role) for role in (getattr(user, "roles", []) or [])]


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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        status = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status, detail=detail) from exc
    return {
        "job_id": job.id,
        "task_type": job.task_type,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@parallel_tasks_router.get("/doc-sync/jobs")
async def list_sync_jobs(
    site_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = DocumentMultiSiteService(db)
    jobs = service.list_sync_jobs(site_id=site_id, limit=limit)
    return {
        "total": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "task_type": job.task_type,
                "status": job.status,
                "attempt_count": int(job.attempt_count or 0),
                "max_attempts": int(job.max_attempts or 0),
                "last_error": job.last_error,
                "payload": job.payload if isinstance(job.payload, dict) else {},
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
            }
            for job in jobs
        ],
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
        raise HTTPException(status_code=404, detail=f"Sync job not found: {job_id}")
    return {
        "id": job.id,
        "task_type": job.task_type,
        "status": job.status,
        "attempt_count": int(job.attempt_count or 0),
        "max_attempts": int(job.max_attempts or 0),
        "last_error": job.last_error,
        "payload": job.payload if isinstance(job.payload, dict) else {},
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "operator_id": int(user.id),
    }


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
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "job_id": new_job.id,
        "task_type": new_job.task_type,
        "status": new_job.status,
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": rule.id,
        "name": rule.name,
        "target_object": rule.target_object,
        "from_state": rule.from_state,
        "to_state": rule.to_state,
        "trigger_phase": rule.trigger_phase,
        "action_type": rule.action_type,
        "fail_strategy": rule.fail_strategy,
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
    return {
        "total": len(rules),
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "target_object": rule.target_object,
                "workflow_map_id": rule.workflow_map_id,
                "from_state": rule.from_state,
                "to_state": rule.to_state,
                "trigger_phase": rule.trigger_phase,
                "action_type": rule.action_type,
                "action_params": rule.action_params or {},
                "fail_strategy": rule.fail_strategy,
                "is_enabled": bool(rule.is_enabled),
            }
            for rule in rules
        ],
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "total": len(runs),
        "runs": [
            {
                "id": run.id,
                "rule_id": run.rule_id,
                "status": run.status,
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
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BreakageIncidentService(db)
    result = service.metrics()
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
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = BreakageIncidentService(db)
    incidents = service.list_incidents(
        status=status,
        severity=severity,
        product_item_id=product_item_id,
        batch_code=batch_code,
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
    export_format: str = Query("zip", description="zip|json"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkorderDocumentPackService(db)
    result = service.export_pack(
        routing_id=routing_id,
        operation_id=operation_id,
        include_inherited=include_inherited,
    )
    manifest = result["manifest"]
    if export_format == "json":
        content = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="workorder-doc-pack.json"'
            },
        )
    if export_format != "zip":
        raise HTTPException(status_code=400, detail="export_format must be zip or json")
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
