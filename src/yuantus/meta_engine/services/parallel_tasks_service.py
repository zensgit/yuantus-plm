from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.meta_engine.models.eco import ECO
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.parallel_tasks import (
    BreakageIncident,
    ConsumptionPlan,
    ConsumptionRecord,
    ECOActivityGate,
    ECOActivityGateEvent,
    RemoteSite,
    ThreeDOverlay,
    WorkflowCustomActionRule,
    WorkflowCustomActionRun,
    WorkorderDocumentLink,
)
from yuantus.meta_engine.services.job_service import JobService


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.utcnow()


def _xor_bytes(raw: bytes, key: bytes) -> bytes:
    if not key:
        return raw
    return bytes(byte ^ key[idx % len(key)] for idx, byte in enumerate(raw))


def _stable_hash(values: Iterable[str]) -> str:
    h = hashlib.sha256()
    for value in values:
        h.update(str(value).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:20]


class DocumentMultiSiteService:
    TASK_PREFIX = "document_sync_"
    _ALLOWED_DIRECTIONS = {"push", "pull"}

    def __init__(self, session: Session):
        self.session = session
        self._job_service = JobService(session)
        settings = get_settings()
        raw_key = (
            (settings.JWT_SECRET_KEY or "yuantus-dev-secret-change-me")
            .encode("utf-8")
        )
        self._cipher_key = hashlib.sha256(raw_key).digest()

    def _encrypt_secret(self, secret: str) -> str:
        encrypted = _xor_bytes(secret.encode("utf-8"), self._cipher_key)
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")

    def _decrypt_secret(self, ciphertext: Optional[str]) -> Optional[str]:
        if not ciphertext:
            return None
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
            plain = _xor_bytes(decoded, self._cipher_key)
            return plain.decode("utf-8")
        except Exception:
            return None

    def upsert_remote_site(
        self,
        *,
        name: str,
        endpoint: str,
        auth_mode: str = "token",
        auth_secret: Optional[str] = None,
        is_active: bool = True,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> RemoteSite:
        site = self.session.query(RemoteSite).filter(RemoteSite.name == name).first()
        if not site:
            site = RemoteSite(id=_uuid(), name=name)
            self.session.add(site)

        site.endpoint = endpoint.rstrip("/")
        site.auth_mode = (auth_mode or "token").strip().lower()
        site.is_active = bool(is_active)
        site.metadata_json = metadata_json or {}
        if auth_secret:
            site.auth_secret_ciphertext = self._encrypt_secret(auth_secret.strip())
        site.updated_at = _utcnow()
        self.session.flush()
        return site

    def list_remote_sites(self, *, active_only: bool = False) -> List[RemoteSite]:
        query = self.session.query(RemoteSite).order_by(RemoteSite.name.asc())
        if active_only:
            query = query.filter(RemoteSite.is_active.is_(True))
        return query.all()

    def get_remote_site(self, site_id: str) -> Optional[RemoteSite]:
        return self.session.get(RemoteSite, site_id)

    def probe_remote_site(
        self, site_id: str, *, timeout_s: float = 3.0
    ) -> Dict[str, Any]:
        site = self.session.get(RemoteSite, site_id)
        if not site:
            raise ValueError(f"Remote site not found: {site_id}")

        target = f"{site.endpoint.rstrip('/')}/health"
        status = "unhealthy"
        detail = ""
        code = None
        try:
            headers = {}
            token = self._decrypt_secret(site.auth_secret_ciphertext)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            with httpx.Client(timeout=timeout_s) as client:
                resp = client.get(target, headers=headers)
            code = int(resp.status_code)
            if 200 <= code < 300:
                status = "healthy"
            else:
                detail = f"http_{code}"
        except Exception as exc:
            detail = str(exc)

        site.last_health_status = status
        site.last_health_error = detail or None
        site.last_health_at = _utcnow()
        self.session.flush()

        return {
            "site_id": site.id,
            "endpoint": site.endpoint,
            "status": status,
            "http_code": code,
            "error": detail or None,
            "checked_at": site.last_health_at.isoformat(),
        }

    def enqueue_sync(
        self,
        *,
        site_id: str,
        direction: str,
        document_ids: List[str],
        user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ConversionJob:
        site = self.session.get(RemoteSite, site_id)
        if not site:
            raise ValueError(f"Remote site not found: {site_id}")
        if not site.is_active:
            raise ValueError(f"Remote site is inactive: {site_id}")

        normalized_direction = (direction or "").strip().lower()
        if normalized_direction not in self._ALLOWED_DIRECTIONS:
            raise ValueError("direction must be push or pull")

        normalized_docs = sorted({str(doc_id).strip() for doc_id in document_ids if str(doc_id).strip()})
        if not normalized_docs:
            raise ValueError("document_ids must not be empty")

        dedupe_key = idempotency_key
        if not dedupe_key:
            dedupe_key = (
                f"doc-sync:{site_id}:{normalized_direction}:{_stable_hash(normalized_docs)}"
            )

        payload = {
            "site_id": site_id,
            "site_name": site.name,
            "endpoint": site.endpoint,
            "direction": normalized_direction,
            "document_ids": normalized_docs,
            "metadata": metadata_json or {},
        }
        return self._job_service.create_job(
            task_type=f"{self.TASK_PREFIX}{normalized_direction}",
            payload=payload,
            user_id=user_id,
            dedupe=True,
            dedupe_key=dedupe_key,
        )

    def get_sync_job(self, job_id: str) -> Optional[ConversionJob]:
        job = self.session.get(ConversionJob, job_id)
        if not job:
            return None
        if not str(job.task_type or "").startswith(self.TASK_PREFIX):
            return None
        return job

    def list_sync_jobs(
        self, *, site_id: Optional[str] = None, limit: int = 100
    ) -> List[ConversionJob]:
        cap = max(1, min(limit, 500))
        query = (
            self.session.query(ConversionJob)
            .filter(ConversionJob.task_type.like(f"{self.TASK_PREFIX}%"))
            .order_by(ConversionJob.created_at.desc())
        )
        jobs = query.limit(cap).all()
        if not site_id:
            return jobs

        target = str(site_id)
        filtered: List[ConversionJob] = []
        for job in jobs:
            payload = job.payload or {}
            if isinstance(payload, dict) and str(payload.get("site_id") or "") == target:
                filtered.append(job)
        return filtered

    def replay_sync_job(
        self, job_id: str, *, user_id: Optional[int] = None
    ) -> ConversionJob:
        job = self.get_sync_job(job_id)
        if not job:
            raise ValueError(f"Sync job not found: {job_id}")
        payload = dict(job.payload or {})
        payload["replay_of"] = job.id
        payload["replayed_at"] = _utcnow().isoformat()
        dedupe_key = f"doc-sync-replay:{job.id}:{_uuid()}"
        return self._job_service.create_job(
            task_type=str(job.task_type),
            payload=payload,
            user_id=user_id,
            dedupe=True,
            dedupe_key=dedupe_key,
        )


class ECOActivityValidationService:
    _TERMINAL = {"completed", "canceled", "exception"}
    _VALID_STATUS = {"pending", "active", "completed", "canceled", "exception"}

    def __init__(self, session: Session):
        self.session = session

    def create_activity(
        self,
        *,
        eco_id: str,
        name: str,
        depends_on_activity_ids: Optional[List[str]] = None,
        is_blocking: bool = True,
        assignee_id: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ECOActivityGate:
        activity = ECOActivityGate(
            id=_uuid(),
            eco_id=eco_id,
            name=name,
            status="pending",
            is_blocking=bool(is_blocking),
            assignee_id=assignee_id,
            depends_on_activity_ids=sorted(
                {
                    str(activity_id).strip()
                    for activity_id in (depends_on_activity_ids or [])
                    if str(activity_id).strip()
                }
            ),
            properties=properties or {},
        )
        self.session.add(activity)
        self.session.flush()
        self._record_event(
            eco_id=eco_id,
            activity_id=activity.id,
            from_status=None,
            to_status="pending",
            reason="created",
            user_id=assignee_id,
        )
        return activity

    def list_activities(self, eco_id: str) -> List[ECOActivityGate]:
        return (
            self.session.query(ECOActivityGate)
            .filter(ECOActivityGate.eco_id == eco_id)
            .order_by(ECOActivityGate.created_at.asc())
            .all()
        )

    def get_activity(self, activity_id: str) -> Optional[ECOActivityGate]:
        return self.session.get(ECOActivityGate, activity_id)

    def _dependency_ids(self, activity: ECOActivityGate) -> List[str]:
        raw = activity.depends_on_activity_ids or []
        if not isinstance(raw, list):
            return []
        result = []
        for value in raw:
            normalized = str(value).strip()
            if normalized:
                result.append(normalized)
        return sorted(set(result))

    def _dependency_blockers(self, activity: ECOActivityGate) -> List[Dict[str, Any]]:
        dep_ids = self._dependency_ids(activity)
        if not dep_ids:
            return []
        blockers: List[Dict[str, Any]] = []
        for dep_id in dep_ids:
            dep = self.session.get(ECOActivityGate, dep_id)
            if not dep:
                blockers.append({"activity_id": dep_id, "reason": "dependency_not_found"})
                continue
            if dep.status != "completed":
                blockers.append(
                    {
                        "activity_id": dep.id,
                        "name": dep.name,
                        "status": dep.status,
                        "reason": "dependency_not_completed",
                    }
                )
        return blockers

    def transition_activity(
        self,
        *,
        activity_id: str,
        to_status: str,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> ECOActivityGate:
        activity = self.session.get(ECOActivityGate, activity_id)
        if not activity:
            raise ValueError(f"Activity not found: {activity_id}")

        target = (to_status or "").strip().lower()
        if target not in self._VALID_STATUS:
            raise ValueError(f"Invalid status: {to_status}")

        if target == "completed":
            blockers = self._dependency_blockers(activity)
            if blockers:
                blocker_text = ", ".join(
                    f"{entry.get('activity_id')}({entry.get('status', entry.get('reason'))})"
                    for entry in blockers
                )
                raise ValueError(f"Blocking dependencies: {blocker_text}")

        from_status = activity.status
        activity.status = target
        activity.updated_at = _utcnow()
        if target in self._TERMINAL:
            activity.closed_at = _utcnow()
            activity.closed_by_id = user_id
        self.session.flush()
        self._record_event(
            eco_id=activity.eco_id,
            activity_id=activity.id,
            from_status=from_status,
            to_status=target,
            reason=reason,
            user_id=user_id,
        )
        return activity

    def blockers_for_eco(self, eco_id: str) -> Dict[str, Any]:
        activities = self.list_activities(eco_id)
        blockers: List[Dict[str, Any]] = []
        for activity in activities:
            if not activity.is_blocking:
                continue
            if activity.status == "completed":
                continue
            deps = self._dependency_blockers(activity)
            blockers.append(
                {
                    "activity_id": activity.id,
                    "name": activity.name,
                    "status": activity.status,
                    "dependencies": deps,
                }
            )
        return {"eco_id": eco_id, "total": len(blockers), "blockers": blockers}

    def recent_events(self, eco_id: str, *, limit: int = 20) -> List[ECOActivityGateEvent]:
        cap = max(1, min(limit, 200))
        return (
            self.session.query(ECOActivityGateEvent)
            .filter(ECOActivityGateEvent.eco_id == eco_id)
            .order_by(ECOActivityGateEvent.created_at.desc())
            .limit(cap)
            .all()
        )

    def _record_event(
        self,
        *,
        eco_id: str,
        activity_id: str,
        from_status: Optional[str],
        to_status: str,
        reason: Optional[str],
        user_id: Optional[int],
    ) -> ECOActivityGateEvent:
        event = ECOActivityGateEvent(
            id=_uuid(),
            eco_id=eco_id,
            activity_id=activity_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            user_id=user_id,
        )
        self.session.add(event)
        self.session.flush()
        return event


class WorkflowCustomActionService:
    _ALLOWED_TYPES = {"emit_event", "create_job", "set_eco_priority"}
    _ALLOWED_PHASES = {"before", "after"}
    _ALLOWED_FAIL = {"block", "warn", "retry"}

    def __init__(self, session: Session):
        self.session = session
        self._job_service = JobService(session)

    def create_rule(
        self,
        *,
        name: str,
        target_object: str,
        from_state: Optional[str],
        to_state: Optional[str],
        trigger_phase: str,
        action_type: str,
        action_params: Optional[Dict[str, Any]] = None,
        fail_strategy: str = "block",
        workflow_map_id: Optional[str] = None,
        is_enabled: bool = True,
    ) -> WorkflowCustomActionRule:
        normalized_phase = (trigger_phase or "before").strip().lower()
        if normalized_phase not in self._ALLOWED_PHASES:
            raise ValueError("trigger_phase must be before or after")
        normalized_action = (action_type or "").strip().lower()
        if normalized_action not in self._ALLOWED_TYPES:
            raise ValueError(
                "action_type must be one of: emit_event, create_job, set_eco_priority"
            )
        normalized_fail = (fail_strategy or "block").strip().lower()
        if normalized_fail not in self._ALLOWED_FAIL:
            raise ValueError("fail_strategy must be one of: block, warn, retry")

        existing = (
            self.session.query(WorkflowCustomActionRule)
            .filter(WorkflowCustomActionRule.name == name)
            .first()
        )
        if existing:
            rule = existing
        else:
            rule = WorkflowCustomActionRule(id=_uuid(), name=name)
            self.session.add(rule)

        rule.target_object = (target_object or "ECO").strip().upper()
        rule.workflow_map_id = workflow_map_id
        rule.from_state = from_state
        rule.to_state = to_state
        rule.trigger_phase = normalized_phase
        rule.action_type = normalized_action
        rule.action_params = action_params or {}
        rule.fail_strategy = normalized_fail
        rule.is_enabled = bool(is_enabled)
        rule.updated_at = _utcnow()
        self.session.flush()
        return rule

    def list_rules(
        self,
        *,
        target_object: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[WorkflowCustomActionRule]:
        query = self.session.query(WorkflowCustomActionRule).order_by(
            WorkflowCustomActionRule.name.asc()
        )
        if enabled_only:
            query = query.filter(WorkflowCustomActionRule.is_enabled.is_(True))
        if target_object:
            query = query.filter(
                WorkflowCustomActionRule.target_object == target_object.strip().upper()
            )
        return query.all()

    def evaluate_transition(
        self,
        *,
        object_id: str,
        target_object: str,
        from_state: Optional[str],
        to_state: Optional[str],
        trigger_phase: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[WorkflowCustomActionRun]:
        normalized_target = (target_object or "ECO").strip().upper()
        normalized_phase = (trigger_phase or "before").strip().lower()
        if normalized_phase not in self._ALLOWED_PHASES:
            raise ValueError("trigger_phase must be before or after")

        query = self.session.query(WorkflowCustomActionRule).filter(
            WorkflowCustomActionRule.is_enabled.is_(True),
            WorkflowCustomActionRule.target_object == normalized_target,
            WorkflowCustomActionRule.trigger_phase == normalized_phase,
        )
        rules = query.order_by(WorkflowCustomActionRule.name.asc()).all()
        runs: List[WorkflowCustomActionRun] = []
        for rule in rules:
            if rule.from_state and str(rule.from_state) != str(from_state):
                continue
            if rule.to_state and str(rule.to_state) != str(to_state):
                continue
            run = self._execute_rule(
                rule=rule,
                object_id=object_id,
                target_object=normalized_target,
                from_state=from_state,
                to_state=to_state,
                trigger_phase=normalized_phase,
                context=context or {},
            )
            runs.append(run)
        return runs

    def _execute_rule(
        self,
        *,
        rule: WorkflowCustomActionRule,
        object_id: str,
        target_object: str,
        from_state: Optional[str],
        to_state: Optional[str],
        trigger_phase: str,
        context: Dict[str, Any],
    ) -> WorkflowCustomActionRun:
        max_attempts = 2 if rule.fail_strategy == "retry" else 1
        attempts = 0
        status = "completed"
        last_error = None
        result: Dict[str, Any] = {}

        while attempts < max_attempts:
            attempts += 1
            try:
                result = self._run_action(
                    rule=rule,
                    object_id=object_id,
                    target_object=target_object,
                    from_state=from_state,
                    to_state=to_state,
                    context=context,
                )
                status = "completed"
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)
                if rule.fail_strategy == "retry" and attempts < max_attempts:
                    continue
                if rule.fail_strategy == "warn":
                    status = "warning"
                else:
                    status = "failed"

        run = WorkflowCustomActionRun(
            id=_uuid(),
            rule_id=rule.id,
            object_id=object_id,
            target_object=target_object,
            from_state=from_state,
            to_state=to_state,
            trigger_phase=trigger_phase,
            status=status,
            attempts=attempts,
            last_error=last_error,
            result=result,
        )
        self.session.add(run)
        self.session.flush()

        if status == "failed" and rule.fail_strategy == "block":
            raise ValueError(last_error or "workflow custom action failed")

        return run

    def _run_action(
        self,
        *,
        rule: WorkflowCustomActionRule,
        object_id: str,
        target_object: str,
        from_state: Optional[str],
        to_state: Optional[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        action = str(rule.action_type or "").strip().lower()
        params = rule.action_params or {}

        if action == "emit_event":
            return {
                "event": params.get("event") or "workflow.transition",
                "object_id": object_id,
                "target_object": target_object,
                "from_state": from_state,
                "to_state": to_state,
                "context": context,
            }

        if action == "create_job":
            task_type = str(params.get("task_type") or "workflow_action")
            payload = {
                "rule_id": rule.id,
                "object_id": object_id,
                "target_object": target_object,
                "from_state": from_state,
                "to_state": to_state,
                "context": context,
                "params": params,
            }
            job = self._job_service.create_job(
                task_type=task_type,
                payload=payload,
                priority=int(params.get("priority") or 10),
                dedupe=True,
                dedupe_key=f"wf-action:{rule.id}:{object_id}:{from_state}:{to_state}",
            )
            return {"job_id": job.id, "task_type": job.task_type}

        if action == "set_eco_priority":
            if target_object != "ECO":
                raise ValueError("set_eco_priority only supports ECO target_object")
            eco = self.session.get(ECO, object_id)
            if not eco:
                raise ValueError(f"ECO not found: {object_id}")
            priority = str(params.get("priority") or "").strip().lower()
            if priority not in {"low", "normal", "high", "urgent"}:
                raise ValueError("priority must be one of: low, normal, high, urgent")
            eco.priority = priority
            eco.updated_at = _utcnow()
            self.session.add(eco)
            self.session.flush()
            return {"eco_id": eco.id, "priority": eco.priority}

        raise ValueError(f"Unsupported action_type: {action}")


class ConsumptionPlanService:
    def __init__(self, session: Session):
        self.session = session

    def create_plan(
        self,
        *,
        name: str,
        planned_quantity: float,
        uom: str = "EA",
        period_unit: str = "week",
        item_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        created_by_id: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ConsumptionPlan:
        plan = ConsumptionPlan(
            id=_uuid(),
            name=name,
            planned_quantity=float(planned_quantity),
            uom=(uom or "EA").strip().upper(),
            period_unit=(period_unit or "week").strip().lower(),
            item_id=item_id,
            period_start=period_start,
            period_end=period_end,
            created_by_id=created_by_id,
            properties=properties or {},
        )
        self.session.add(plan)
        self.session.flush()
        return plan

    def list_plans(
        self, *, state: Optional[str] = None, item_id: Optional[str] = None
    ) -> List[ConsumptionPlan]:
        query = self.session.query(ConsumptionPlan).order_by(ConsumptionPlan.created_at.desc())
        if state:
            query = query.filter(ConsumptionPlan.state == state)
        if item_id:
            query = query.filter(ConsumptionPlan.item_id == item_id)
        return query.all()

    def add_actual(
        self,
        *,
        plan_id: str,
        actual_quantity: float,
        source_type: str = "workorder",
        source_id: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ConsumptionRecord:
        plan = self.session.get(ConsumptionPlan, plan_id)
        if not plan:
            raise ValueError(f"Consumption plan not found: {plan_id}")
        record = ConsumptionRecord(
            id=_uuid(),
            plan_id=plan.id,
            source_type=(source_type or "workorder").strip().lower(),
            source_id=source_id,
            actual_quantity=float(actual_quantity),
            recorded_at=recorded_at or _utcnow(),
            properties=properties or {},
        )
        self.session.add(record)
        self.session.flush()
        return record

    def variance(self, plan_id: str) -> Dict[str, Any]:
        plan = self.session.get(ConsumptionPlan, plan_id)
        if not plan:
            raise ValueError(f"Consumption plan not found: {plan_id}")
        records = (
            self.session.query(ConsumptionRecord)
            .filter(ConsumptionRecord.plan_id == plan_id)
            .all()
        )
        actual_total = sum(float(record.actual_quantity or 0.0) for record in records)
        planned = float(plan.planned_quantity or 0.0)
        delta = actual_total - planned
        delta_ratio = (delta / planned) if planned else None
        return {
            "plan_id": plan_id,
            "planned_quantity": planned,
            "actual_quantity": actual_total,
            "delta_quantity": delta,
            "delta_ratio": delta_ratio,
            "uom": plan.uom,
            "records": len(records),
        }

    def dashboard(self, *, item_id: Optional[str] = None) -> Dict[str, Any]:
        plans = self.list_plans(item_id=item_id)
        rows = []
        for plan in plans:
            row = self.variance(plan.id)
            row["name"] = plan.name
            row["state"] = plan.state
            row["item_id"] = plan.item_id
            rows.append(row)
        return {"total": len(rows), "plans": rows}


class BreakageIncidentService:
    def __init__(self, session: Session):
        self.session = session
        self._job_service = JobService(session)

    def create_incident(
        self,
        *,
        description: str,
        severity: str = "medium",
        status: str = "open",
        product_item_id: Optional[str] = None,
        bom_line_item_id: Optional[str] = None,
        production_order_id: Optional[str] = None,
        version_id: Optional[str] = None,
        batch_code: Optional[str] = None,
        customer_name: Optional[str] = None,
        responsibility: Optional[str] = None,
        created_by_id: Optional[int] = None,
    ) -> BreakageIncident:
        incident = BreakageIncident(
            id=_uuid(),
            description=description.strip(),
            severity=(severity or "medium").strip().lower(),
            status=(status or "open").strip().lower(),
            product_item_id=product_item_id,
            bom_line_item_id=bom_line_item_id,
            production_order_id=production_order_id,
            version_id=version_id,
            batch_code=batch_code,
            customer_name=customer_name,
            responsibility=responsibility,
            created_by_id=created_by_id,
        )
        self.session.add(incident)
        self.session.flush()
        return incident

    def get_incident(self, incident_id: str) -> Optional[BreakageIncident]:
        return self.session.get(BreakageIncident, incident_id)

    def list_incidents(
        self,
        *,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        product_item_id: Optional[str] = None,
        batch_code: Optional[str] = None,
    ) -> List[BreakageIncident]:
        query = self.session.query(BreakageIncident).order_by(
            BreakageIncident.created_at.desc()
        )
        if status:
            query = query.filter(BreakageIncident.status == status)
        if severity:
            query = query.filter(BreakageIncident.severity == severity)
        if product_item_id:
            query = query.filter(BreakageIncident.product_item_id == product_item_id)
        if batch_code:
            query = query.filter(BreakageIncident.batch_code == batch_code)
        return query.all()

    def update_status(self, incident_id: str, *, status: str) -> BreakageIncident:
        incident = self.session.get(BreakageIncident, incident_id)
        if not incident:
            raise ValueError(f"Breakage incident not found: {incident_id}")
        incident.status = status.strip().lower()
        incident.updated_at = _utcnow()
        self.session.flush()
        return incident

    def metrics(self) -> Dict[str, Any]:
        incidents = (
            self.session.query(BreakageIncident)
            .order_by(BreakageIncident.created_at.desc())
            .all()
        )
        by_signature = defaultdict(int)
        for incident in incidents:
            signature = (
                str(incident.product_item_id or ""),
                (incident.description or "").strip().lower(),
            )
            by_signature[signature] += 1

        repeated_events = sum(count for count in by_signature.values() if count > 1)
        total = len(incidents)
        repeated_rate = (repeated_events / total) if total else 0.0

        hotspot_counter = Counter(
            str(incident.bom_line_item_id)
            for incident in incidents
            if incident.bom_line_item_id
        )
        hotspot_components = [
            {"bom_line_item_id": item_id, "count": count}
            for item_id, count in hotspot_counter.most_common(10)
        ]

        by_status = Counter(str(incident.status or "unknown") for incident in incidents)
        by_severity = Counter(
            str(incident.severity or "unknown") for incident in incidents
        )
        return {
            "total": total,
            "repeated_failure_rate": repeated_rate,
            "repeated_event_count": repeated_events,
            "by_status": dict(by_status),
            "by_severity": dict(by_severity),
            "hotspot_components": hotspot_components,
        }

    def enqueue_helpdesk_stub_sync(
        self,
        incident_id: str,
        *,
        user_id: Optional[int] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> ConversionJob:
        incident = self.session.get(BreakageIncident, incident_id)
        if not incident:
            raise ValueError(f"Breakage incident not found: {incident_id}")

        payload = {
            "incident_id": incident.id,
            "description": incident.description,
            "severity": incident.severity,
            "status": incident.status,
            "product_item_id": incident.product_item_id,
            "batch_code": incident.batch_code,
            "customer_name": incident.customer_name,
            "metadata": metadata_json or {},
            "mode": "helpdesk_stub",
        }
        dedupe_key = f"breakage-helpdesk:{incident.id}:{incident.updated_at.isoformat() if incident.updated_at else ''}"
        return self._job_service.create_job(
            task_type="breakage_helpdesk_sync_stub",
            payload=payload,
            user_id=user_id,
            dedupe=True,
            dedupe_key=dedupe_key,
        )


class WorkorderDocumentPackService:
    def __init__(self, session: Session):
        self.session = session

    def upsert_link(
        self,
        *,
        routing_id: str,
        document_item_id: str,
        operation_id: Optional[str] = None,
        inherit_to_children: bool = True,
        visible_in_production: bool = True,
    ) -> WorkorderDocumentLink:
        existing = (
            self.session.query(WorkorderDocumentLink)
            .filter(
                WorkorderDocumentLink.routing_id == routing_id,
                WorkorderDocumentLink.operation_id == operation_id,
                WorkorderDocumentLink.document_item_id == document_item_id,
            )
            .first()
        )
        if existing:
            link = existing
        else:
            link = WorkorderDocumentLink(
                id=_uuid(),
                routing_id=routing_id,
                operation_id=operation_id,
                document_item_id=document_item_id,
            )
            self.session.add(link)

        link.inherit_to_children = bool(inherit_to_children)
        link.visible_in_production = bool(visible_in_production)
        self.session.flush()
        return link

    def list_links(
        self,
        *,
        routing_id: str,
        operation_id: Optional[str] = None,
        include_inherited: bool = True,
    ) -> List[WorkorderDocumentLink]:
        query = (
            self.session.query(WorkorderDocumentLink)
            .filter(
                WorkorderDocumentLink.routing_id == routing_id,
                WorkorderDocumentLink.visible_in_production.is_(True),
            )
            .order_by(
                WorkorderDocumentLink.operation_id.asc(),
                WorkorderDocumentLink.created_at.asc(),
            )
        )
        links = query.all()
        if operation_id is None:
            return links

        filtered: List[WorkorderDocumentLink] = []
        for link in links:
            if link.operation_id == operation_id:
                filtered.append(link)
                continue
            if include_inherited and link.operation_id is None and link.inherit_to_children:
                filtered.append(link)
        return filtered

    def export_pack(
        self,
        *,
        routing_id: str,
        operation_id: Optional[str] = None,
        include_inherited: bool = True,
    ) -> Dict[str, Any]:
        links = self.list_links(
            routing_id=routing_id,
            operation_id=operation_id,
            include_inherited=include_inherited,
        )
        docs = [
            {
                "link_id": link.id,
                "routing_id": link.routing_id,
                "operation_id": link.operation_id,
                "document_item_id": link.document_item_id,
                "inherit_to_children": bool(link.inherit_to_children),
                "visible_in_production": bool(link.visible_in_production),
                "created_at": link.created_at.isoformat() if link.created_at else None,
            }
            for link in links
        ]
        manifest = {
            "generated_at": _utcnow().isoformat(),
            "routing_id": routing_id,
            "operation_id": operation_id,
            "count": len(docs),
            "documents": docs,
        }

        csv_io = io.StringIO()
        writer = csv.DictWriter(
            csv_io,
            fieldnames=[
                "link_id",
                "routing_id",
                "operation_id",
                "document_item_id",
                "inherit_to_children",
                "visible_in_production",
                "created_at",
            ],
        )
        writer.writeheader()
        for row in docs:
            writer.writerow(row)

        zip_io = io.BytesIO()
        with ZipFile(zip_io, mode="w", compression=ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            zf.writestr("documents.csv", csv_io.getvalue())

        return {"manifest": manifest, "zip_bytes": zip_io.getvalue()}


class ThreeDOverlayService:
    def __init__(self, session: Session):
        self.session = session

    def upsert_overlay(
        self,
        *,
        document_item_id: str,
        version_label: Optional[str] = None,
        status: Optional[str] = None,
        visibility_role: Optional[str] = None,
        part_refs: Optional[List[Dict[str, Any]]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ThreeDOverlay:
        overlay = (
            self.session.query(ThreeDOverlay)
            .filter(ThreeDOverlay.document_item_id == document_item_id)
            .first()
        )
        if not overlay:
            overlay = ThreeDOverlay(id=_uuid(), document_item_id=document_item_id)
            self.session.add(overlay)

        overlay.version_label = version_label
        overlay.status = status
        overlay.visibility_role = visibility_role
        overlay.part_refs = part_refs or []
        overlay.properties = properties or {}
        overlay.updated_at = _utcnow()
        self.session.flush()
        return overlay

    def get_overlay(
        self, *, document_item_id: str, user_roles: Optional[List[str]] = None
    ) -> Optional[ThreeDOverlay]:
        overlay = (
            self.session.query(ThreeDOverlay)
            .filter(ThreeDOverlay.document_item_id == document_item_id)
            .first()
        )
        if not overlay:
            return None

        required_role = (overlay.visibility_role or "").strip().lower()
        if required_role:
            actual_roles = {str(role).strip().lower() for role in (user_roles or [])}
            if required_role not in actual_roles:
                raise PermissionError("Overlay is not visible for current roles")

        return overlay

    def resolve_component(
        self,
        *,
        document_item_id: str,
        component_ref: str,
        user_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        overlay = self.get_overlay(document_item_id=document_item_id, user_roles=user_roles)
        if not overlay:
            raise ValueError(f"Overlay not found: {document_item_id}")

        refs = overlay.part_refs or []
        if not isinstance(refs, list):
            refs = []
        normalized_ref = str(component_ref).strip().lower()
        for row in refs:
            if not isinstance(row, dict):
                continue
            candidate = str(row.get("component_ref") or "").strip().lower()
            if candidate == normalized_ref:
                return {
                    "document_item_id": document_item_id,
                    "component_ref": component_ref,
                    "hit": row,
                }
        raise ValueError(f"Component not found: {component_ref}")
