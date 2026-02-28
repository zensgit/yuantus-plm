from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from threading import Lock
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.meta_engine.models.eco import ECO
from yuantus.meta_engine.models.job import ConversionJob, JobStatus
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
    _ALLOWED_JOB_STATUS = {
        JobStatus.PENDING.value,
        JobStatus.PROCESSING.value,
        JobStatus.COMPLETED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
    }

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

    def _normalize_job_status(self, status: str) -> str:
        normalized = (status or "").strip().lower()
        if normalized not in self._ALLOWED_JOB_STATUS:
            allowed = ", ".join(sorted(self._ALLOWED_JOB_STATUS))
            raise ValueError(f"status must be one of: {allowed}")
        return normalized

    def _resolve_retry_attempts(self, metadata_json: Optional[Dict[str, Any]]) -> int:
        default_attempts = max(1, int(get_settings().JOB_MAX_ATTEMPTS_DEFAULT or 1))
        if not isinstance(metadata_json, dict):
            return default_attempts
        configured = metadata_json.get("retry_max_attempts")
        if configured is None:
            return default_attempts
        try:
            attempts = int(configured)
        except Exception as exc:
            raise ValueError("retry_max_attempts must be an integer between 1 and 10") from exc
        if attempts < 1 or attempts > 10:
            raise ValueError("retry_max_attempts must be between 1 and 10")
        return attempts

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

        metadata = metadata_json if isinstance(metadata_json, dict) else {}
        dedupe_key = idempotency_key
        if not dedupe_key:
            dedupe_key = (
                f"doc-sync:{site_id}:{normalized_direction}:{_stable_hash(normalized_docs)}"
            )
        retry_attempts = self._resolve_retry_attempts(metadata)
        payload_hash = _stable_hash(
            [
                site_id,
                normalized_direction,
                ",".join(normalized_docs),
                json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            ]
        )
        trace_id = _uuid()
        now_iso = _utcnow().isoformat()

        existing = (
            self.session.query(ConversionJob)
            .filter(
                ConversionJob.task_type == f"{self.TASK_PREFIX}{normalized_direction}",
                ConversionJob.dedupe_key == dedupe_key,
                ConversionJob.status.in_(
                    [JobStatus.PENDING.value, JobStatus.PROCESSING.value]
                ),
            )
            .order_by(ConversionJob.created_at.desc())
            .first()
        )
        if existing:
            existing_payload = (
                dict(existing.payload) if isinstance(existing.payload, dict) else {}
            )
            existing_payload["idempotency_conflicts"] = int(
                existing_payload.get("idempotency_conflicts") or 0
            ) + 1
            existing_payload["idempotency_last_seen_at"] = now_iso
            existing_payload["idempotency_last_request"] = {
                "site_id": site_id,
                "direction": normalized_direction,
                "document_ids": normalized_docs,
                "trace_id": trace_id,
                "payload_hash": payload_hash,
            }
            existing.payload = existing_payload
            self.session.flush()
            return existing

        payload = {
            "site_id": site_id,
            "site_name": site.name,
            "endpoint": site.endpoint,
            "direction": normalized_direction,
            "document_ids": normalized_docs,
            "metadata": metadata,
            "sync_trace": {
                "trace_id": trace_id,
                "origin_site": site.name,
                "payload_hash": payload_hash,
                "created_at": now_iso,
            },
            "retry_policy": {"max_attempts": retry_attempts},
            "idempotency_conflicts": 0,
        }
        return self._job_service.create_job(
            task_type=f"{self.TASK_PREFIX}{normalized_direction}",
            payload=payload,
            user_id=user_id,
            max_attempts=retry_attempts,
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
        self,
        *,
        site_id: Optional[str] = None,
        status: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ConversionJob]:
        cap = max(1, min(limit, 500))
        query = (
            self.session.query(ConversionJob)
            .filter(ConversionJob.task_type.like(f"{self.TASK_PREFIX}%"))
            .order_by(ConversionJob.created_at.desc())
        )
        if status:
            query = query.filter(
                ConversionJob.status == self._normalize_job_status(status)
            )
        if created_from:
            query = query.filter(ConversionJob.created_at >= created_from)
        if created_to:
            query = query.filter(ConversionJob.created_at <= created_to)
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

    def build_sync_job_view(self, job: ConversionJob) -> Dict[str, Any]:
        payload = job.payload if isinstance(job.payload, dict) else {}
        trace = payload.get("sync_trace")
        if not isinstance(trace, dict):
            trace = {}
        retry_policy = payload.get("retry_policy")
        if not isinstance(retry_policy, dict):
            retry_policy = {}
        attempt_count = int(job.attempt_count or 0)
        max_attempts = int(job.max_attempts or retry_policy.get("max_attempts") or 0)
        remaining_attempts = (
            max(max_attempts - attempt_count, 0) if max_attempts > 0 else None
        )
        dead_letter = payload.get("dead_letter")
        if not isinstance(dead_letter, dict):
            dead_letter = {}
        is_dead_letter = bool(dead_letter.get("is_dead_letter")) or (
            str(job.status or "").lower() == JobStatus.FAILED.value
            and max_attempts > 0
            and attempt_count >= max_attempts
        )
        dead_letter_reason = (
            dead_letter.get("reason") if dead_letter.get("reason") else None
        ) or (job.last_error if is_dead_letter else None)

        return {
            "id": job.id,
            "task_type": job.task_type,
            "status": job.status,
            "attempt_count": attempt_count,
            "max_attempts": max_attempts,
            "last_error": job.last_error,
            "payload": payload,
            "dedupe_key": job.dedupe_key,
            "sync_trace": {
                "trace_id": trace.get("trace_id"),
                "origin_site": trace.get("origin_site"),
                "payload_hash": trace.get("payload_hash"),
            },
            "idempotency_conflicts": int(payload.get("idempotency_conflicts") or 0),
            "retry_budget": {
                "attempt_count": attempt_count,
                "max_attempts": max_attempts,
                "remaining_attempts": remaining_attempts,
            },
            "is_dead_letter": is_dead_letter,
            "dead_letter_reason": dead_letter_reason,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

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
    _RESULT_OK = "OK"
    _RESULT_WARN = "WARN"
    _RESULT_BLOCK = "BLOCK"
    _RESULT_RETRY_EXHAUSTED = "RETRY_EXHAUSTED"

    def __init__(self, session: Session):
        self.session = session
        self._job_service = JobService(session)

    def _normalize_retry_max(self, fail_strategy: str, params: Dict[str, Any]) -> int:
        if fail_strategy != "retry":
            return 0
        raw = params.get("max_retries", 1)
        try:
            value = int(raw)
        except Exception as exc:
            raise ValueError("max_retries must be an integer between 1 and 5") from exc
        if value < 1 or value > 5:
            raise ValueError("max_retries must be between 1 and 5 for retry strategy")
        return value

    def _normalize_priority(self, params: Dict[str, Any]) -> int:
        raw = params.get("priority", 100)
        try:
            value = int(raw)
        except Exception as exc:
            raise ValueError("priority must be an integer between 0 and 1000") from exc
        if value < 0 or value > 1000:
            raise ValueError("priority must be between 0 and 1000")
        return value

    def _normalize_timeout_s(self, params: Dict[str, Any]) -> float:
        raw = params.get("timeout_s", 5.0)
        try:
            value = float(raw)
        except Exception as exc:
            raise ValueError("timeout_s must be a number between 0.01 and 60") from exc
        if value < 0.01 or value > 60:
            raise ValueError("timeout_s must be between 0.01 and 60")
        return value

    def _normalize_action_params(
        self, params: Optional[Dict[str, Any]], fail_strategy: str
    ) -> Dict[str, Any]:
        normalized = dict(params or {})
        normalized["priority"] = self._normalize_priority(normalized)
        normalized["timeout_s"] = self._normalize_timeout_s(normalized)
        normalized["max_retries"] = self._normalize_retry_max(fail_strategy, normalized)
        return normalized

    def _rule_priority(self, rule: WorkflowCustomActionRule) -> int:
        params = rule.action_params if isinstance(rule.action_params, dict) else {}
        try:
            return int(params.get("priority") or 100)
        except Exception:
            return 100

    def _rule_timeout(self, rule: WorkflowCustomActionRule) -> float:
        params = rule.action_params if isinstance(rule.action_params, dict) else {}
        value = params.get("timeout_s", 5.0)
        try:
            return float(value)
        except Exception:
            return 5.0

    def _rule_max_retries(self, rule: WorkflowCustomActionRule) -> int:
        params = rule.action_params if isinstance(rule.action_params, dict) else {}
        try:
            return int(params.get("max_retries") or 0)
        except Exception:
            return 0

    def _find_scope_conflicts(
        self,
        *,
        target_object: str,
        trigger_phase: str,
        from_state: Optional[str],
        to_state: Optional[str],
        workflow_map_id: Optional[str],
        exclude_rule_id: Optional[str] = None,
    ) -> List[WorkflowCustomActionRule]:
        query = self.session.query(WorkflowCustomActionRule).filter(
            WorkflowCustomActionRule.is_enabled.is_(True),
            WorkflowCustomActionRule.target_object == target_object,
            WorkflowCustomActionRule.trigger_phase == trigger_phase,
            WorkflowCustomActionRule.from_state == from_state,
            WorkflowCustomActionRule.to_state == to_state,
            WorkflowCustomActionRule.workflow_map_id == workflow_map_id,
        )
        rules = query.order_by(WorkflowCustomActionRule.name.asc()).all()
        if not exclude_rule_id:
            return rules
        return [rule for rule in rules if str(rule.id) != str(exclude_rule_id)]

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
        normalized_params = self._normalize_action_params(action_params, normalized_fail)

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
        conflicts = self._find_scope_conflicts(
            target_object=(target_object or "ECO").strip().upper(),
            trigger_phase=normalized_phase,
            from_state=from_state,
            to_state=to_state,
            workflow_map_id=workflow_map_id,
            exclude_rule_id=rule.id,
        )
        if conflicts:
            normalized_params["conflict_scope"] = {
                "count": len(conflicts),
                "rule_ids": [entry.id for entry in conflicts[:20]],
            }
        else:
            normalized_params.pop("conflict_scope", None)
        rule.action_params = normalized_params
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
        matched: List[WorkflowCustomActionRule] = []
        for rule in rules:
            if rule.from_state and str(rule.from_state) != str(from_state):
                continue
            if rule.to_state and str(rule.to_state) != str(to_state):
                continue
            matched.append(rule)

        matched.sort(
            key=lambda rule: (
                self._rule_priority(rule),
                str(rule.name or ""),
                str(rule.id or ""),
            )
        )
        runs: List[WorkflowCustomActionRun] = []
        for idx, rule in enumerate(matched, start=1):
            run = self._execute_rule(
                rule=rule,
                object_id=object_id,
                target_object=normalized_target,
                from_state=from_state,
                to_state=to_state,
                trigger_phase=normalized_phase,
                context=context or {},
                execution_order=idx,
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
        execution_order: int,
    ) -> WorkflowCustomActionRun:
        max_retries = self._rule_max_retries(rule)
        max_attempts = 1 + max_retries if rule.fail_strategy == "retry" else 1
        timeout_s = self._rule_timeout(rule)
        attempts = 0
        status = "completed"
        last_error = None
        result: Dict[str, Any] = {}
        result_code = self._RESULT_OK

        while attempts < max_attempts:
            attempts += 1
            started = time.monotonic()
            try:
                result = self._run_action(
                    rule=rule,
                    object_id=object_id,
                    target_object=target_object,
                    from_state=from_state,
                    to_state=to_state,
                    context=context,
                )
                elapsed_s = time.monotonic() - started
                if elapsed_s > timeout_s:
                    raise TimeoutError(
                        f"workflow custom action timeout: {elapsed_s:.3f}s > {timeout_s:.3f}s"
                    )
                status = "completed"
                last_error = None
                result_code = self._RESULT_OK
                break
            except Exception as exc:
                last_error = str(exc)
                if rule.fail_strategy == "retry" and attempts < max_attempts:
                    continue
                if rule.fail_strategy == "warn":
                    status = "warning"
                    result_code = self._RESULT_WARN
                elif rule.fail_strategy == "retry":
                    status = "failed"
                    result_code = self._RESULT_RETRY_EXHAUSTED
                else:
                    status = "failed"
                    result_code = self._RESULT_BLOCK

        if not isinstance(result, dict):
            result = {"value": result}
        result["result_code"] = result_code
        result["execution"] = {
            "order": int(execution_order),
            "priority": int(self._rule_priority(rule)),
            "timeout_s": float(timeout_s),
            "max_retries": int(max_retries),
        }
        if last_error:
            result["error"] = last_error

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
            raise ValueError(
                f"[{result_code}] {last_error or 'workflow custom action failed'}"
            )

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

    def _template_key_from_plan(self, plan: ConsumptionPlan) -> Optional[str]:
        props = plan.properties if isinstance(plan.properties, dict) else {}
        template = props.get("template")
        if not isinstance(template, dict):
            return None
        key = str(template.get("key") or "").strip()
        return key or None

    def _template_meta_from_plan(self, plan: ConsumptionPlan) -> Dict[str, Any]:
        props = plan.properties if isinstance(plan.properties, dict) else {}
        template = props.get("template")
        if not isinstance(template, dict):
            template = {}
        return {
            "key": str(template.get("key") or "").strip() or None,
            "version": str(template.get("version") or "").strip() or None,
            "is_template_version": bool(template.get("is_template_version")),
            "is_active": bool(template.get("is_active")),
        }

    def _plans_for_template(self, template_key: str) -> List[ConsumptionPlan]:
        key = str(template_key or "").strip()
        if not key:
            return []
        plans = (
            self.session.query(ConsumptionPlan)
            .order_by(ConsumptionPlan.created_at.desc())
            .all()
        )
        return [
            plan
            for plan in plans
            if self._template_key_from_plan(plan) == key
            and bool(self._template_meta_from_plan(plan).get("is_template_version"))
        ]

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
        state: str = "active",
    ) -> ConsumptionPlan:
        plan = ConsumptionPlan(
            id=_uuid(),
            name=name,
            state=(state or "active").strip().lower(),
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

    def create_template_version(
        self,
        *,
        template_key: str,
        name: str,
        planned_quantity: float,
        version_label: Optional[str] = None,
        uom: str = "EA",
        period_unit: str = "week",
        item_id: Optional[str] = None,
        activate: bool = True,
        created_by_id: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ConsumptionPlan:
        key = str(template_key or "").strip()
        if not key:
            raise ValueError("template_key must not be empty")

        existing = self._plans_for_template(key)
        if version_label:
            normalized_version = str(version_label).strip()
        else:
            normalized_version = f"v{len(existing) + 1}"

        props = dict(properties or {})
        template_props = props.get("template")
        if not isinstance(template_props, dict):
            template_props = {}
        template_props.update(
            {
                "key": key,
                "version": normalized_version,
                "is_template_version": True,
                "is_active": bool(activate),
            }
        )
        props["template"] = template_props

        plan = self.create_plan(
            name=name,
            planned_quantity=planned_quantity,
            uom=uom,
            period_unit=period_unit,
            item_id=item_id,
            created_by_id=created_by_id,
            properties=props,
            state="active" if activate else "inactive",
        )
        if activate:
            for other in existing:
                if other.id == plan.id:
                    continue
                other_props = (
                    dict(other.properties) if isinstance(other.properties, dict) else {}
                )
                other_template = other_props.get("template")
                if not isinstance(other_template, dict):
                    other_template = {}
                other_template["is_active"] = False
                other_props["template"] = other_template
                other.properties = other_props
                other.state = "inactive"
                other.updated_at = _utcnow()
                self.session.add(other)
        self.session.flush()
        return plan

    def list_template_versions(
        self, template_key: str, *, include_inactive: bool = True
    ) -> List[Dict[str, Any]]:
        plans = self._plans_for_template(template_key)
        rows: List[Dict[str, Any]] = []
        for plan in plans:
            meta = self._template_meta_from_plan(plan)
            if not include_inactive and not meta.get("is_active"):
                continue
            rows.append(
                {
                    "id": plan.id,
                    "name": plan.name,
                    "state": plan.state,
                    "planned_quantity": float(plan.planned_quantity or 0.0),
                    "uom": plan.uom,
                    "period_unit": plan.period_unit,
                    "item_id": plan.item_id,
                    "template": meta,
                    "created_at": plan.created_at.isoformat() if plan.created_at else None,
                    "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
                }
            )
        return rows

    def set_template_version_state(
        self,
        plan_id: str,
        *,
        activate: bool,
    ) -> ConsumptionPlan:
        plan = self.session.get(ConsumptionPlan, plan_id)
        if not plan:
            raise ValueError(f"Consumption plan not found: {plan_id}")
        meta = self._template_meta_from_plan(plan)
        key = meta.get("key")
        if not key or not meta.get("is_template_version"):
            raise ValueError("plan is not a template version")

        props = dict(plan.properties or {})
        template = props.get("template")
        if not isinstance(template, dict):
            template = {}
        template["is_active"] = bool(activate)
        props["template"] = template
        plan.properties = props
        plan.state = "active" if activate else "inactive"
        plan.updated_at = _utcnow()
        self.session.add(plan)

        if activate:
            for other in self._plans_for_template(str(key)):
                if other.id == plan.id:
                    continue
                other_props = (
                    dict(other.properties) if isinstance(other.properties, dict) else {}
                )
                other_template = other_props.get("template")
                if not isinstance(other_template, dict):
                    other_template = {}
                other_template["is_active"] = False
                other_props["template"] = other_template
                other.properties = other_props
                other.state = "inactive"
                other.updated_at = _utcnow()
                self.session.add(other)
        self.session.flush()
        return plan

    def preview_template_impact(
        self,
        *,
        template_key: str,
        planned_quantity: float,
        uom: Optional[str] = None,
        period_unit: Optional[str] = None,
    ) -> Dict[str, Any]:
        versions = self.list_template_versions(template_key, include_inactive=True)
        active = next(
            (row for row in versions if bool((row.get("template") or {}).get("is_active"))),
            None,
        )
        candidate_qty = float(planned_quantity)
        baseline_qty = float(active.get("planned_quantity") or 0.0) if active else 0.0
        delta_qty = candidate_qty - baseline_qty

        impacts = []
        for row in versions:
            row_qty = float(row.get("planned_quantity") or 0.0)
            impacts.append(
                {
                    "plan_id": row.get("id"),
                    "name": row.get("name"),
                    "template_version": (row.get("template") or {}).get("version"),
                    "is_active": bool((row.get("template") or {}).get("is_active")),
                    "current_quantity": row_qty,
                    "candidate_quantity": candidate_qty,
                    "delta_quantity": candidate_qty - row_qty,
                }
            )

        return {
            "template_key": str(template_key),
            "candidate": {
                "planned_quantity": candidate_qty,
                "uom": (uom or (active.get("uom") if active else "EA")),
                "period_unit": (period_unit or (active.get("period_unit") if active else "week")),
            },
            "active_version": active,
            "summary": {
                "versions_total": len(versions),
                "impacted_versions": len(impacts),
                "baseline_quantity": baseline_qty,
                "candidate_quantity": candidate_qty,
                "delta_quantity": delta_qty,
            },
            "impacts": impacts,
        }

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

    def _normalize_trend_window_days(self, window_days: int) -> int:
        allowed = {7, 14, 30}
        try:
            value = int(window_days)
        except Exception as exc:
            raise ValueError("trend_window_days must be one of: 7, 14, 30") from exc
        if value not in allowed:
            raise ValueError("trend_window_days must be one of: 7, 14, 30")
        return value

    def _normalize_page(self, page: int) -> int:
        value = int(page or 1)
        return 1 if value < 1 else value

    def _normalize_page_size(self, page_size: int) -> int:
        value = int(page_size or 20)
        if value < 1:
            value = 1
        if value > 200:
            value = 200
        return value

    def _apply_incident_filters(
        self,
        incidents: List[BreakageIncident],
        *,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        product_item_id: Optional[str] = None,
        batch_code: Optional[str] = None,
        responsibility: Optional[str] = None,
    ) -> List[BreakageIncident]:
        filtered: List[BreakageIncident] = []
        normalized_status = (status or "").strip().lower()
        normalized_severity = (severity or "").strip().lower()
        normalized_product = str(product_item_id or "").strip()
        normalized_batch = str(batch_code or "").strip()
        normalized_resp = str(responsibility or "").strip().lower()

        for incident in incidents:
            if normalized_status and str(incident.status or "").lower() != normalized_status:
                continue
            if normalized_severity and str(incident.severity or "").lower() != normalized_severity:
                continue
            if normalized_product and str(incident.product_item_id or "") != normalized_product:
                continue
            if normalized_batch and str(incident.batch_code or "") != normalized_batch:
                continue
            if normalized_resp and str(incident.responsibility or "").strip().lower() != normalized_resp:
                continue
            filtered.append(incident)
        return filtered

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
        responsibility: Optional[str] = None,
    ) -> List[BreakageIncident]:
        incidents = (
            self.session.query(BreakageIncident)
            .order_by(BreakageIncident.created_at.desc())
            .all()
        )
        return self._apply_incident_filters(
            incidents,
            status=status,
            severity=severity,
            product_item_id=product_item_id,
            batch_code=batch_code,
            responsibility=responsibility,
        )

    def update_status(self, incident_id: str, *, status: str) -> BreakageIncident:
        incident = self.session.get(BreakageIncident, incident_id)
        if not incident:
            raise ValueError(f"Breakage incident not found: {incident_id}")
        incident.status = status.strip().lower()
        incident.updated_at = _utcnow()
        self.session.flush()
        return incident

    def metrics(
        self,
        *,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        product_item_id: Optional[str] = None,
        batch_code: Optional[str] = None,
        responsibility: Optional[str] = None,
        trend_window_days: int = 14,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        window_days = self._normalize_trend_window_days(trend_window_days)
        current_page = self._normalize_page(page)
        current_page_size = self._normalize_page_size(page_size)
        incidents_all = (
            self.session.query(BreakageIncident)
            .order_by(BreakageIncident.created_at.desc())
            .all()
        )
        incidents = self._apply_incident_filters(
            incidents_all,
            status=status,
            severity=severity,
            product_item_id=product_item_id,
            batch_code=batch_code,
            responsibility=responsibility,
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
        by_responsibility = Counter(
            str(incident.responsibility or "unknown") for incident in incidents
        )

        now = _utcnow()
        start_day = (now - timedelta(days=window_days - 1)).date()
        day_keys = [
            (start_day + timedelta(days=offset)).isoformat()
            for offset in range(window_days)
        ]
        trend_counter = {day: 0 for day in day_keys}
        for incident in incidents:
            created_at = incident.created_at or incident.updated_at
            if not created_at:
                continue
            day = created_at.date().isoformat()
            if day in trend_counter:
                trend_counter[day] += 1
        trend = [{"date": day, "count": trend_counter[day]} for day in day_keys]

        total = len(incidents)
        total_pages = max(1, (total + current_page_size - 1) // current_page_size)
        if current_page > total_pages:
            current_page = total_pages
        offset = (current_page - 1) * current_page_size
        page_rows = incidents[offset : offset + current_page_size]

        incidents_page = [
            {
                "id": incident.id,
                "description": incident.description,
                "status": incident.status,
                "severity": incident.severity,
                "product_item_id": incident.product_item_id,
                "bom_line_item_id": incident.bom_line_item_id,
                "batch_code": incident.batch_code,
                "responsibility": incident.responsibility,
                "created_at": incident.created_at.isoformat() if incident.created_at else None,
                "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
            }
            for incident in page_rows
        ]

        return {
            "total": total,
            "repeated_failure_rate": repeated_rate,
            "repeated_event_count": repeated_events,
            "by_status": dict(by_status),
            "by_severity": dict(by_severity),
            "by_responsibility": dict(by_responsibility),
            "hotspot_components": hotspot_components,
            "trend_window_days": window_days,
            "trend": trend,
            "filters": {
                "status": status,
                "severity": severity,
                "product_item_id": product_item_id,
                "batch_code": batch_code,
                "responsibility": responsibility,
            },
            "pagination": {
                "page": current_page,
                "page_size": current_page_size,
                "pages": total_pages,
                "total": total,
            },
            "incidents": incidents_page,
        }

    def _metrics_export_rows(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        filters = metrics.get("filters") if isinstance(metrics.get("filters"), dict) else {}
        trend = metrics.get("trend") if isinstance(metrics.get("trend"), list) else []
        rows: List[Dict[str, Any]] = []
        for point in trend:
            if not isinstance(point, dict):
                continue
            rows.append(
                {
                    "date": point.get("date"),
                    "count": point.get("count"),
                    "total": metrics.get("total"),
                    "repeated_event_count": metrics.get("repeated_event_count"),
                    "repeated_failure_rate": metrics.get("repeated_failure_rate"),
                    "trend_window_days": metrics.get("trend_window_days"),
                    "status_filter": filters.get("status"),
                    "severity_filter": filters.get("severity"),
                    "product_item_id_filter": filters.get("product_item_id"),
                    "batch_code_filter": filters.get("batch_code"),
                    "responsibility_filter": filters.get("responsibility"),
                }
            )
        if rows:
            return rows
        return [
            {
                "date": None,
                "count": 0,
                "total": metrics.get("total"),
                "repeated_event_count": metrics.get("repeated_event_count"),
                "repeated_failure_rate": metrics.get("repeated_failure_rate"),
                "trend_window_days": metrics.get("trend_window_days"),
                "status_filter": filters.get("status"),
                "severity_filter": filters.get("severity"),
                "product_item_id_filter": filters.get("product_item_id"),
                "batch_code_filter": filters.get("batch_code"),
                "responsibility_filter": filters.get("responsibility"),
            }
        ]

    def export_metrics(
        self,
        *,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        product_item_id: Optional[str] = None,
        batch_code: Optional[str] = None,
        responsibility: Optional[str] = None,
        trend_window_days: int = 14,
        page: int = 1,
        page_size: int = 20,
        export_format: str = "json",
    ) -> Dict[str, Any]:
        metrics = self.metrics(
            status=status,
            severity=severity,
            product_item_id=product_item_id,
            batch_code=batch_code,
            responsibility=responsibility,
            trend_window_days=trend_window_days,
            page=page,
            page_size=page_size,
        )
        normalized = str(export_format or "json").strip().lower()
        if normalized == "json":
            content = json.dumps(metrics, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "content": content,
                "media_type": "application/json",
                "filename": "breakage-metrics.json",
            }

        rows = self._metrics_export_rows(metrics)
        if normalized == "csv":
            csv_io = io.StringIO()
            writer = csv.DictWriter(
                csv_io,
                fieldnames=[
                    "date",
                    "count",
                    "total",
                    "repeated_event_count",
                    "repeated_failure_rate",
                    "trend_window_days",
                    "status_filter",
                    "severity_filter",
                    "product_item_id_filter",
                    "batch_code_filter",
                    "responsibility_filter",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            return {
                "content": csv_io.getvalue().encode("utf-8"),
                "media_type": "text/csv",
                "filename": "breakage-metrics.csv",
            }

        if normalized == "md":
            by_status = (
                metrics.get("by_status")
                if isinstance(metrics.get("by_status"), dict)
                else {}
            )
            by_severity = (
                metrics.get("by_severity")
                if isinstance(metrics.get("by_severity"), dict)
                else {}
            )
            by_responsibility = (
                metrics.get("by_responsibility")
                if isinstance(metrics.get("by_responsibility"), dict)
                else {}
            )
            hotspots = (
                metrics.get("hotspot_components")
                if isinstance(metrics.get("hotspot_components"), list)
                else []
            )
            lines = [
                "# Breakage Metrics",
                "",
                f"- total: {metrics.get('total') or 0}",
                (
                    f"- repeated_event_count: "
                    f"{metrics.get('repeated_event_count') or 0}"
                ),
                (
                    f"- repeated_failure_rate: "
                    f"{metrics.get('repeated_failure_rate') or 0}"
                ),
                f"- trend_window_days: {metrics.get('trend_window_days') or ''}",
                "",
                f"- by_status: {json.dumps(by_status, ensure_ascii=False)}",
                f"- by_severity: {json.dumps(by_severity, ensure_ascii=False)}",
                (
                    f"- by_responsibility: "
                    f"{json.dumps(by_responsibility, ensure_ascii=False)}"
                ),
                (
                    f"- hotspot_components: "
                    f"{json.dumps(hotspots, ensure_ascii=False)}"
                ),
                "",
                "| Date | Count |",
                "| --- | --- |",
            ]
            for row in rows:
                lines.append(f"| {row['date'] or ''} | {row['count'] or 0} |")
            return {
                "content": ("\n".join(lines) + "\n").encode("utf-8"),
                "media_type": "text/markdown",
                "filename": "breakage-metrics.md",
            }

        raise ValueError("export_format must be json, csv or md")

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
        export_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        links = self.list_links(
            routing_id=routing_id,
            operation_id=operation_id,
            include_inherited=include_inherited,
        )
        generated_at = _utcnow().isoformat()
        normalized_meta = export_meta if isinstance(export_meta, dict) else {}
        operator_id = normalized_meta.get("operator_id")
        try:
            operator_id = int(operator_id) if operator_id is not None else None
        except Exception:
            operator_id = None
        export_context = {
            "generated_at": generated_at,
            "job_no": str(normalized_meta.get("job_no") or "").strip() or None,
            "operator_id": operator_id,
            "operator_name": str(normalized_meta.get("operator_name") or "").strip() or None,
            "exported_by": str(normalized_meta.get("exported_by") or "").strip() or None,
            "format_version": "workorder-doc-pack.v2",
        }
        docs = [
            {
                "link_id": link.id,
                "routing_id": link.routing_id,
                "operation_id": link.operation_id,
                "document_item_id": link.document_item_id,
                "inherit_to_children": bool(link.inherit_to_children),
                "visible_in_production": bool(link.visible_in_production),
                "document_scope": "routing" if link.operation_id is None else "operation",
                "created_at": link.created_at.isoformat() if link.created_at else None,
            }
            for link in links
        ]
        scope_counter = Counter(
            str(row.get("document_scope") or "unknown")
            for row in docs
        )
        manifest = {
            "generated_at": generated_at,
            "routing_id": routing_id,
            "operation_id": operation_id,
            "count": len(docs),
            "scope_summary": dict(scope_counter),
            "export_meta": export_context,
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
                "document_scope",
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
    _CACHE_TTL_SECONDS = 60
    _CACHE_MAX_ENTRIES = 500
    _CACHE_LOCK = Lock()
    _CACHE: Dict[str, Dict[str, Any]] = {}
    _CACHE_HITS = 0
    _CACHE_MISSES = 0
    _CACHE_EVICTIONS = 0

    def __init__(self, session: Session):
        self.session = session

    @classmethod
    def _cache_now(cls) -> float:
        return time.monotonic()

    @classmethod
    def _cache_key(cls, document_item_id: str) -> str:
        return str(document_item_id or "").strip()

    @classmethod
    def _prune_cache_locked(cls, *, now: Optional[float] = None) -> None:
        ts = cls._cache_now() if now is None else float(now)
        expired = [
            key
            for key, row in cls._CACHE.items()
            if float((row or {}).get("expires_at") or 0.0) <= ts
        ]
        for key in expired:
            cls._CACHE.pop(key, None)

        overflow = len(cls._CACHE) - int(cls._CACHE_MAX_ENTRIES)
        if overflow <= 0:
            return

        rows = sorted(
            cls._CACHE.items(),
            key=lambda pair: float((pair[1] or {}).get("stored_at") or 0.0),
        )
        for key, _ in rows[:overflow]:
            cls._CACHE.pop(key, None)
            cls._CACHE_EVICTIONS += 1

    @classmethod
    def reset_cache_for_tests(cls) -> None:
        with cls._CACHE_LOCK:
            cls._CACHE = {}
            cls._CACHE_HITS = 0
            cls._CACHE_MISSES = 0
            cls._CACHE_EVICTIONS = 0

    @classmethod
    def cache_stats(cls) -> Dict[str, Any]:
        with cls._CACHE_LOCK:
            cls._prune_cache_locked()
            return {
                "entries": len(cls._CACHE),
                "hits": int(cls._CACHE_HITS),
                "misses": int(cls._CACHE_MISSES),
                "evictions": int(cls._CACHE_EVICTIONS),
                "ttl_seconds": int(cls._CACHE_TTL_SECONDS),
                "max_entries": int(cls._CACHE_MAX_ENTRIES),
            }

    def _cache_get(self, document_item_id: str) -> Optional[Dict[str, Any]]:
        cls = type(self)
        key = self._cache_key(document_item_id)
        if not key:
            return None
        now = self._cache_now()
        with cls._CACHE_LOCK:
            cls._prune_cache_locked(now=now)
            row = cls._CACHE.get(key)
            if not row:
                cls._CACHE_MISSES += 1
                return None
            cls._CACHE_HITS += 1
            payload = row.get("payload")
            return dict(payload) if isinstance(payload, dict) else None

    def _cache_set(self, document_item_id: str, payload: Dict[str, Any]) -> None:
        cls = type(self)
        key = self._cache_key(document_item_id)
        if not key:
            return
        now = self._cache_now()
        row = {
            "payload": dict(payload),
            "stored_at": now,
            "expires_at": now + float(cls._CACHE_TTL_SECONDS),
        }
        with cls._CACHE_LOCK:
            cls._CACHE[key] = row
            cls._prune_cache_locked(now=now)

    def _cache_invalidate(self, document_item_id: str) -> None:
        cls = type(self)
        key = self._cache_key(document_item_id)
        if not key:
            return
        with cls._CACHE_LOCK:
            cls._CACHE.pop(key, None)

    def _serialize_overlay(self, overlay: ThreeDOverlay) -> Dict[str, Any]:
        part_refs = overlay.part_refs if isinstance(overlay.part_refs, list) else []
        properties = overlay.properties if isinstance(overlay.properties, dict) else {}
        return {
            "id": overlay.id,
            "document_item_id": overlay.document_item_id,
            "version_label": overlay.version_label,
            "status": overlay.status,
            "visibility_role": overlay.visibility_role,
            "part_refs": list(part_refs),
            "properties": dict(properties),
            "created_at": overlay.created_at,
            "updated_at": overlay.updated_at,
        }

    def _overlay_from_payload(self, payload: Dict[str, Any]) -> SimpleNamespace:
        part_refs = payload.get("part_refs")
        properties = payload.get("properties")
        return SimpleNamespace(
            id=payload.get("id"),
            document_item_id=payload.get("document_item_id"),
            version_label=payload.get("version_label"),
            status=payload.get("status"),
            visibility_role=payload.get("visibility_role"),
            part_refs=list(part_refs) if isinstance(part_refs, list) else [],
            properties=dict(properties) if isinstance(properties, dict) else {},
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
        )

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
        self._cache_invalidate(document_item_id)
        self._cache_set(document_item_id, self._serialize_overlay(overlay))
        return overlay

    def get_overlay(
        self, *, document_item_id: str, user_roles: Optional[List[str]] = None
    ) -> Optional[SimpleNamespace]:
        payload = self._cache_get(document_item_id)
        if payload is None:
            overlay = (
                self.session.query(ThreeDOverlay)
                .filter(ThreeDOverlay.document_item_id == document_item_id)
                .first()
            )
            if not overlay:
                return None
            payload = self._serialize_overlay(overlay)
            self._cache_set(document_item_id, payload)

        required_role = str(payload.get("visibility_role") or "").strip().lower()
        if required_role:
            actual_roles = {str(role).strip().lower() for role in (user_roles or [])}
            if required_role not in actual_roles:
                raise PermissionError("Overlay is not visible for current roles")

        return self._overlay_from_payload(payload)

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

    def resolve_components(
        self,
        *,
        document_item_id: str,
        component_refs: List[str],
        user_roles: Optional[List[str]] = None,
        include_missing: bool = True,
    ) -> Dict[str, Any]:
        overlay = self.get_overlay(document_item_id=document_item_id, user_roles=user_roles)
        if not overlay:
            raise ValueError(f"Overlay not found: {document_item_id}")

        refs = overlay.part_refs or []
        if not isinstance(refs, list):
            refs = []
        index: Dict[str, Dict[str, Any]] = {}
        for row in refs:
            if not isinstance(row, dict):
                continue
            key = str(row.get("component_ref") or "").strip().lower()
            if key and key not in index:
                index[key] = row

        normalized_refs = [str(ref).strip() for ref in (component_refs or []) if str(ref).strip()]
        rows: List[Dict[str, Any]] = []
        hit_count = 0
        for ref in normalized_refs:
            hit = index.get(ref.lower())
            if hit is not None:
                hit_count += 1
                rows.append(
                    {
                        "component_ref": ref,
                        "found": True,
                        "hit": hit,
                    }
                )
                continue
            if include_missing:
                rows.append(
                    {
                        "component_ref": ref,
                        "found": False,
                        "hit": None,
                    }
                )

        return {
            "document_item_id": document_item_id,
            "requested": len(normalized_refs),
            "returned": len(rows),
            "hits": hit_count,
            "misses": len(normalized_refs) - hit_count,
            "include_missing": bool(include_missing),
            "results": rows,
            "cache": self.cache_stats(),
        }


class ParallelOpsOverviewService:
    _ALLOWED_WINDOW_DAYS = {1, 7, 14, 30, 90}
    _ALLOWED_BUCKET_DAYS = {1, 7, 14, 30}
    _DEFAULT_SLO_THRESHOLDS = {
        "overlay_cache_hit_rate_warn": 0.8,
        "overlay_cache_min_requests_warn": 10,
        "doc_sync_dead_letter_rate_warn": 0.05,
        "workflow_failed_rate_warn": 0.02,
        "breakage_open_rate_warn": 0.5,
    }

    def __init__(self, session: Session):
        self.session = session

    def _normalize_window_days(self, window_days: int) -> int:
        try:
            value = int(window_days)
        except Exception as exc:
            raise ValueError("window_days must be one of: 1, 7, 14, 30, 90") from exc
        if value not in self._ALLOWED_WINDOW_DAYS:
            raise ValueError("window_days must be one of: 1, 7, 14, 30, 90")
        return value

    def _window_since(self, window_days: int) -> datetime:
        return _utcnow() - timedelta(days=window_days)

    def _safe_ratio(self, numerator: int, denominator: int) -> Optional[float]:
        return (float(numerator) / float(denominator)) if denominator > 0 else None

    def _normalize_rate_threshold(self, value: Optional[float], *, field: str) -> Optional[float]:
        if value is None:
            return None
        try:
            normalized = float(value)
        except Exception as exc:
            raise ValueError(f"{field} must be between 0 and 1") from exc
        if normalized < 0.0 or normalized > 1.0:
            raise ValueError(f"{field} must be between 0 and 1")
        return normalized

    def _normalize_non_negative_int(self, value: Optional[int], *, field: str) -> Optional[int]:
        if value is None:
            return None
        try:
            normalized = int(value)
        except Exception as exc:
            raise ValueError(f"{field} must be >= 0") from exc
        if normalized < 0:
            raise ValueError(f"{field} must be >= 0")
        return normalized

    def _normalize_page(self, page: int) -> int:
        try:
            value = int(page or 1)
        except Exception as exc:
            raise ValueError("page must be >= 1") from exc
        if value < 1:
            raise ValueError("page must be >= 1")
        return value

    def _normalize_page_size(self, page_size: int) -> int:
        try:
            value = int(page_size or 20)
        except Exception as exc:
            raise ValueError("page_size must be between 1 and 200") from exc
        if value < 1 or value > 200:
            raise ValueError("page_size must be between 1 and 200")
        return value

    def _normalize_bucket_days(self, bucket_days: int) -> int:
        try:
            value = int(bucket_days or 1)
        except Exception as exc:
            raise ValueError("bucket_days must be one of: 1, 7, 14, 30") from exc
        if value not in self._ALLOWED_BUCKET_DAYS:
            raise ValueError("bucket_days must be one of: 1, 7, 14, 30")
        return value

    def _paginate(
        self, rows: List[Dict[str, Any]], *, page: int, page_size: int
    ) -> Dict[str, Any]:
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": ((total + page_size - 1) // page_size) if page_size else 0,
            "rows": rows[start:end],
        }

    def _doc_sync_summary(
        self,
        *,
        since: datetime,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        jobs = (
            self.session.query(ConversionJob)
            .filter(ConversionJob.task_type.like("document_sync_%"))
            .filter(ConversionJob.created_at >= since)
            .order_by(ConversionJob.created_at.desc())
            .all()
        )
        filtered: List[ConversionJob] = []
        for job in jobs:
            payload = job.payload if isinstance(job.payload, dict) else {}
            if site_id and str(payload.get("site_id") or "").strip() != str(site_id).strip():
                continue
            filtered.append(job)

        by_status = Counter(str(job.status or "unknown").lower() for job in filtered)
        dead_letter = [
            job
            for job in filtered
            if str(job.status or "").lower() == JobStatus.FAILED.value
            and int(job.max_attempts or 0) > 0
            and int(job.attempt_count or 0) >= int(job.max_attempts or 0)
        ]
        success_count = int(by_status.get(JobStatus.COMPLETED.value, 0))
        total = len(filtered)
        avg_attempts = (
            sum(int(job.attempt_count or 0) for job in filtered) / float(total)
            if total > 0
            else 0.0
        )
        return {
            "total": total,
            "by_status": dict(by_status),
            "success_rate": self._safe_ratio(success_count, total),
            "dead_letter_total": len(dead_letter),
            "dead_letter_rate": self._safe_ratio(len(dead_letter), total),
            "avg_attempt_count": round(avg_attempts, 4),
            "site_filter": site_id,
        }

    def _workflow_summary(
        self,
        *,
        since: datetime,
        target_object: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = self.session.query(WorkflowCustomActionRun).filter(
            WorkflowCustomActionRun.created_at >= since
        )
        if target_object:
            query = query.filter(WorkflowCustomActionRun.target_object == target_object)
        runs = query.order_by(WorkflowCustomActionRun.created_at.desc()).all()

        by_status = Counter(str(run.status or "unknown").lower() for run in runs)
        by_result_code = Counter(
            str((run.result or {}).get("result_code") or "UNKNOWN")
            for run in runs
            if isinstance(run.result, dict)
        )
        failed_count = int(by_status.get("failed", 0))
        warning_count = int(by_status.get("warning", 0))
        total = len(runs)
        return {
            "total": total,
            "by_status": dict(by_status),
            "by_result_code": dict(by_result_code),
            "failed_rate": self._safe_ratio(failed_count, total),
            "warning_rate": self._safe_ratio(warning_count, total),
            "target_object_filter": target_object,
        }

    def _breakage_summary(self, *, since: datetime) -> Dict[str, Any]:
        incidents = (
            self.session.query(BreakageIncident)
            .filter(BreakageIncident.created_at >= since)
            .order_by(BreakageIncident.created_at.desc())
            .all()
        )
        total = len(incidents)
        by_status = Counter(str(row.status or "unknown").lower() for row in incidents)
        by_severity = Counter(str(row.severity or "unknown").lower() for row in incidents)
        by_responsibility = Counter(
            str(row.responsibility or "unassigned") for row in incidents
        )
        open_total = int(by_status.get("open", 0))
        descriptions = Counter(str(row.description or "").strip().lower() for row in incidents)
        repeated_total = sum(
            count
            for key, count in descriptions.items()
            if key and count > 1
        )
        return {
            "total": total,
            "by_status": dict(by_status),
            "by_severity": dict(by_severity),
            "by_responsibility": dict(by_responsibility),
            "open_total": open_total,
            "open_rate": self._safe_ratio(open_total, total),
            "repeated_total": repeated_total,
            "repeated_rate": self._safe_ratio(repeated_total, total),
        }

    def _consumption_template_summary(
        self, *, template_key: Optional[str] = None
    ) -> Dict[str, Any]:
        plans = (
            self.session.query(ConsumptionPlan)
            .order_by(ConsumptionPlan.created_at.desc())
            .all()
        )
        template_rows: List[ConsumptionPlan] = []
        for plan in plans:
            props = plan.properties if isinstance(plan.properties, dict) else {}
            template = props.get("template")
            if not isinstance(template, dict):
                continue
            if not bool(template.get("is_template_version")):
                continue
            key = str(template.get("key") or "").strip()
            if not key:
                continue
            if template_key and key != str(template_key).strip():
                continue
            template_rows.append(plan)

        active_by_key: Counter = Counter()
        all_keys = set()
        for row in template_rows:
            props = row.properties if isinstance(row.properties, dict) else {}
            template = props.get("template")
            if not isinstance(template, dict):
                continue
            key = str(template.get("key") or "").strip()
            if not key:
                continue
            all_keys.add(key)
            if bool(template.get("is_active")):
                active_by_key[key] += 1

        invalid_templates = [key for key, count in active_by_key.items() if count != 1]
        templates_without_active = [key for key in all_keys if active_by_key.get(key, 0) == 0]

        return {
            "versions_total": len(template_rows),
            "templates_total": len(all_keys),
            "active_versions_total": int(sum(active_by_key.values())),
            "invalid_active_templates": sorted(invalid_templates),
            "templates_without_active": sorted(templates_without_active),
            "template_key_filter": template_key,
        }

    def _overlay_cache_summary(self) -> Dict[str, Any]:
        cache = ThreeDOverlayService.cache_stats()
        requests = int(cache.get("hits") or 0) + int(cache.get("misses") or 0)
        hit_rate = self._safe_ratio(int(cache.get("hits") or 0), requests)
        return {
            **cache,
            "requests": requests,
            "hit_rate": hit_rate,
        }

    def summary(
        self,
        *,
        window_days: int = 7,
        site_id: Optional[str] = None,
        target_object: Optional[str] = None,
        template_key: Optional[str] = None,
        overlay_cache_hit_rate_warn: Optional[float] = None,
        overlay_cache_min_requests_warn: Optional[int] = None,
        doc_sync_dead_letter_rate_warn: Optional[float] = None,
        workflow_failed_rate_warn: Optional[float] = None,
        breakage_open_rate_warn: Optional[float] = None,
    ) -> Dict[str, Any]:
        normalized_window = self._normalize_window_days(window_days)
        since = self._window_since(normalized_window)
        thresholds = {
            "overlay_cache_hit_rate_warn": (
                self._normalize_rate_threshold(
                    overlay_cache_hit_rate_warn,
                    field="overlay_cache_hit_rate_warn",
                )
                if overlay_cache_hit_rate_warn is not None
                else float(self._DEFAULT_SLO_THRESHOLDS["overlay_cache_hit_rate_warn"])
            ),
            "overlay_cache_min_requests_warn": (
                self._normalize_non_negative_int(
                    overlay_cache_min_requests_warn,
                    field="overlay_cache_min_requests_warn",
                )
                if overlay_cache_min_requests_warn is not None
                else int(self._DEFAULT_SLO_THRESHOLDS["overlay_cache_min_requests_warn"])
            ),
            "doc_sync_dead_letter_rate_warn": (
                self._normalize_rate_threshold(
                    doc_sync_dead_letter_rate_warn,
                    field="doc_sync_dead_letter_rate_warn",
                )
                if doc_sync_dead_letter_rate_warn is not None
                else float(self._DEFAULT_SLO_THRESHOLDS["doc_sync_dead_letter_rate_warn"])
            ),
            "workflow_failed_rate_warn": (
                self._normalize_rate_threshold(
                    workflow_failed_rate_warn,
                    field="workflow_failed_rate_warn",
                )
                if workflow_failed_rate_warn is not None
                else float(self._DEFAULT_SLO_THRESHOLDS["workflow_failed_rate_warn"])
            ),
            "breakage_open_rate_warn": (
                self._normalize_rate_threshold(
                    breakage_open_rate_warn,
                    field="breakage_open_rate_warn",
                )
                if breakage_open_rate_warn is not None
                else float(self._DEFAULT_SLO_THRESHOLDS["breakage_open_rate_warn"])
            ),
        }

        doc_sync = self._doc_sync_summary(since=since, site_id=site_id)
        workflow = self._workflow_summary(since=since, target_object=target_object)
        breakages = self._breakage_summary(since=since)
        consumption_templates = self._consumption_template_summary(
            template_key=template_key
        )
        overlay_cache = self._overlay_cache_summary()

        hints: List[Dict[str, Any]] = []
        if (
            overlay_cache.get("requests", 0)
            >= int(thresholds["overlay_cache_min_requests_warn"])
            and (overlay_cache.get("hit_rate") or 0.0)
            < float(thresholds["overlay_cache_hit_rate_warn"])
        ):
            hints.append(
                {
                    "code": "overlay_cache_hit_rate_low",
                    "level": "warn",
                    "message": (
                        "Overlay cache hit rate is below "
                        f"{float(thresholds['overlay_cache_hit_rate_warn']):.4f} "
                        "in current process window"
                    ),
                }
            )
        if (doc_sync.get("dead_letter_rate") or 0.0) > float(
            thresholds["doc_sync_dead_letter_rate_warn"]
        ):
            hints.append(
                {
                    "code": "doc_sync_dead_letter_rate_high",
                    "level": "warn",
                    "message": (
                        "Document sync dead-letter rate is above "
                        f"{float(thresholds['doc_sync_dead_letter_rate_warn']):.4f}"
                    ),
                }
            )
        if (workflow.get("failed_rate") or 0.0) > float(
            thresholds["workflow_failed_rate_warn"]
        ):
            hints.append(
                {
                    "code": "workflow_action_failed_rate_high",
                    "level": "warn",
                    "message": (
                        "Workflow custom action failed rate is above "
                        f"{float(thresholds['workflow_failed_rate_warn']):.4f}"
                    ),
                }
            )
        if (breakages.get("open_rate") or 0.0) > float(
            thresholds["breakage_open_rate_warn"]
        ):
            hints.append(
                {
                    "code": "breakage_open_rate_high",
                    "level": "warn",
                    "message": (
                        "Open breakage ratio is above "
                        f"{float(thresholds['breakage_open_rate_warn']):.4f}"
                    ),
                }
            )

        return {
            "generated_at": _utcnow().isoformat(),
            "window_days": normalized_window,
            "window_since": since.isoformat(),
            "doc_sync": doc_sync,
            "workflow_actions": workflow,
            "breakages": breakages,
            "consumption_templates": consumption_templates,
            "overlay_cache": overlay_cache,
            "slo_hints": hints,
            "slo_thresholds": thresholds,
        }

    def trends(
        self,
        *,
        window_days: int = 7,
        bucket_days: int = 1,
        site_id: Optional[str] = None,
        target_object: Optional[str] = None,
        template_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_window = self._normalize_window_days(window_days)
        normalized_bucket = self._normalize_bucket_days(bucket_days)
        if normalized_bucket > normalized_window:
            raise ValueError("bucket_days must be <= window_days")

        since = self._window_since(normalized_window)
        now = _utcnow()
        bucket_span = timedelta(days=normalized_bucket)

        points: List[Dict[str, Any]] = []
        cursor = since
        while cursor < now:
            bucket_end = min(cursor + bucket_span, now)
            points.append(
                {
                    "bucket_start": cursor.isoformat(),
                    "bucket_end": bucket_end.isoformat(),
                    "doc_sync": {
                        "total": 0,
                        "failed_total": 0,
                        "dead_letter_total": 0,
                    },
                    "workflow_actions": {
                        "total": 0,
                        "failed_total": 0,
                    },
                    "breakages": {
                        "total": 0,
                        "open_total": 0,
                    },
                    "_doc_sync_success_total": 0,
                }
            )
            cursor = bucket_end

        if not points:
            points.append(
                {
                    "bucket_start": since.isoformat(),
                    "bucket_end": now.isoformat(),
                    "doc_sync": {
                        "total": 0,
                        "failed_total": 0,
                        "dead_letter_total": 0,
                    },
                    "workflow_actions": {
                        "total": 0,
                        "failed_total": 0,
                    },
                    "breakages": {
                        "total": 0,
                        "open_total": 0,
                    },
                    "_doc_sync_success_total": 0,
                }
            )

        bucket_seconds = float(bucket_span.total_seconds())

        def bucket_index(created_at: Optional[datetime]) -> Optional[int]:
            if created_at is None:
                return None
            delta = (created_at - since).total_seconds()
            if delta < 0:
                return None
            idx = int(delta // bucket_seconds) if bucket_seconds > 0 else 0
            if idx < 0:
                return None
            if idx >= len(points):
                return len(points) - 1
            return idx

        jobs = (
            self.session.query(ConversionJob)
            .filter(ConversionJob.task_type.like("document_sync_%"))
            .filter(ConversionJob.created_at >= since)
            .all()
        )
        for job in jobs:
            payload = job.payload if isinstance(job.payload, dict) else {}
            row_site_id = str(payload.get("site_id") or "").strip()
            if site_id and row_site_id != str(site_id).strip():
                continue
            idx = bucket_index(job.created_at)
            if idx is None:
                continue
            row = points[idx]
            doc_sync = row["doc_sync"]
            doc_sync["total"] += 1
            status = str(job.status or "").lower()
            if status == JobStatus.COMPLETED.value:
                row["_doc_sync_success_total"] += 1
            if status == JobStatus.FAILED.value:
                doc_sync["failed_total"] += 1
                max_attempts = int(job.max_attempts or 0)
                attempt_count = int(job.attempt_count or 0)
                if max_attempts > 0 and attempt_count >= max_attempts:
                    doc_sync["dead_letter_total"] += 1

        workflow_query = self.session.query(WorkflowCustomActionRun).filter(
            WorkflowCustomActionRun.created_at >= since
        )
        if target_object:
            workflow_query = workflow_query.filter(
                WorkflowCustomActionRun.target_object == target_object
            )
        for run in workflow_query.all():
            idx = bucket_index(run.created_at)
            if idx is None:
                continue
            row = points[idx]
            workflow = row["workflow_actions"]
            workflow["total"] += 1
            if str(run.status or "").lower() == "failed":
                workflow["failed_total"] += 1

        incidents = (
            self.session.query(BreakageIncident)
            .filter(BreakageIncident.created_at >= since)
            .all()
        )
        for incident in incidents:
            idx = bucket_index(incident.created_at)
            if idx is None:
                continue
            row = points[idx]
            breakages = row["breakages"]
            breakages["total"] += 1
            if str(incident.status or "").lower() == "open":
                breakages["open_total"] += 1

        for row in points:
            doc_sync = row["doc_sync"]
            success_total = int(row.pop("_doc_sync_success_total", 0))
            doc_sync["success_rate"] = self._safe_ratio(success_total, doc_sync["total"])
            doc_sync["dead_letter_rate"] = self._safe_ratio(
                doc_sync["dead_letter_total"],
                doc_sync["total"],
            )

            workflow = row["workflow_actions"]
            workflow["failed_rate"] = self._safe_ratio(
                workflow["failed_total"],
                workflow["total"],
            )

            breakages = row["breakages"]
            breakages["open_rate"] = self._safe_ratio(
                breakages["open_total"],
                breakages["total"],
            )

        return {
            "generated_at": now.isoformat(),
            "window_days": normalized_window,
            "window_since": since.isoformat(),
            "bucket_days": normalized_bucket,
            "filters": {
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
            },
            "points": points,
            "aggregates": {
                "doc_sync_total": int(sum((row["doc_sync"]["total"] or 0) for row in points)),
                "doc_sync_failed_total": int(
                    sum((row["doc_sync"]["failed_total"] or 0) for row in points)
                ),
                "doc_sync_dead_letter_total": int(
                    sum((row["doc_sync"]["dead_letter_total"] or 0) for row in points)
                ),
                "workflow_total": int(
                    sum((row["workflow_actions"]["total"] or 0) for row in points)
                ),
                "workflow_failed_total": int(
                    sum((row["workflow_actions"]["failed_total"] or 0) for row in points)
                ),
                "breakages_total": int(sum((row["breakages"]["total"] or 0) for row in points)),
                "breakages_open_total": int(
                    sum((row["breakages"]["open_total"] or 0) for row in points)
                ),
            },
            "consumption_templates": self._consumption_template_summary(
                template_key=template_key
            ),
            "overlay_cache": self._overlay_cache_summary(),
        }

    def doc_sync_failures(
        self,
        *,
        window_days: int = 7,
        site_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        normalized_window = self._normalize_window_days(window_days)
        normalized_page = self._normalize_page(page)
        normalized_page_size = self._normalize_page_size(page_size)
        since = self._window_since(normalized_window)

        jobs = (
            self.session.query(ConversionJob)
            .filter(ConversionJob.task_type.like("document_sync_%"))
            .filter(ConversionJob.status == JobStatus.FAILED.value)
            .filter(ConversionJob.created_at >= since)
            .order_by(ConversionJob.created_at.desc())
            .all()
        )
        rows: List[Dict[str, Any]] = []
        for job in jobs:
            payload = job.payload if isinstance(job.payload, dict) else {}
            row_site_id = str(payload.get("site_id") or "").strip() or None
            if site_id and row_site_id != str(site_id).strip():
                continue
            rows.append(
                {
                    "id": job.id,
                    "task_type": job.task_type,
                    "status": job.status,
                    "attempt_count": int(job.attempt_count or 0),
                    "max_attempts": int(job.max_attempts or 0),
                    "last_error": job.last_error,
                    "dedupe_key": job.dedupe_key,
                    "site_id": row_site_id,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                }
            )

        paged = self._paginate(rows, page=normalized_page, page_size=normalized_page_size)
        return {
            "window_days": normalized_window,
            "window_since": since.isoformat(),
            "site_filter": site_id,
            "total": paged["total"],
            "pagination": {
                "page": paged["page"],
                "page_size": paged["page_size"],
                "pages": paged["pages"],
                "total": paged["total"],
            },
            "jobs": paged["rows"],
        }

    def workflow_failures(
        self,
        *,
        window_days: int = 7,
        target_object: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        normalized_window = self._normalize_window_days(window_days)
        normalized_page = self._normalize_page(page)
        normalized_page_size = self._normalize_page_size(page_size)
        since = self._window_since(normalized_window)

        query = (
            self.session.query(WorkflowCustomActionRun)
            .filter(WorkflowCustomActionRun.status == "failed")
            .filter(WorkflowCustomActionRun.created_at >= since)
        )
        if target_object:
            query = query.filter(WorkflowCustomActionRun.target_object == target_object)
        runs = query.order_by(WorkflowCustomActionRun.created_at.desc()).all()

        rows: List[Dict[str, Any]] = []
        for run in runs:
            result = run.result if isinstance(run.result, dict) else {}
            rows.append(
                {
                    "id": run.id,
                    "rule_id": run.rule_id,
                    "object_id": run.object_id,
                    "target_object": run.target_object,
                    "from_state": run.from_state,
                    "to_state": run.to_state,
                    "trigger_phase": run.trigger_phase,
                    "status": run.status,
                    "attempts": int(run.attempts or 0),
                    "result_code": result.get("result_code"),
                    "last_error": run.last_error,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                }
            )

        paged = self._paginate(rows, page=normalized_page, page_size=normalized_page_size)
        return {
            "window_days": normalized_window,
            "window_since": since.isoformat(),
            "target_object_filter": target_object,
            "total": paged["total"],
            "pagination": {
                "page": paged["page"],
                "page_size": paged["page_size"],
                "pages": paged["pages"],
                "total": paged["total"],
            },
            "runs": paged["rows"],
        }

    def _prometheus_escape(self, value: Any) -> str:
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace('"', '\\"')
        )

    def _prometheus_line(
        self,
        name: str,
        value: Optional[float],
        *,
        labels: Optional[Dict[str, Any]] = None,
    ) -> str:
        metric_value = float(value) if value is not None else 0.0
        label_rows = []
        for key, raw in sorted((labels or {}).items()):
            if raw is None:
                continue
            label_rows.append(f'{key}="{self._prometheus_escape(raw)}"')
        if label_rows:
            return f"{name}{{{','.join(label_rows)}}} {metric_value}"
        return f"{name} {metric_value}"

    def prometheus_metrics(
        self,
        *,
        window_days: int = 7,
        site_id: Optional[str] = None,
        target_object: Optional[str] = None,
        template_key: Optional[str] = None,
        overlay_cache_hit_rate_warn: Optional[float] = None,
        overlay_cache_min_requests_warn: Optional[int] = None,
        doc_sync_dead_letter_rate_warn: Optional[float] = None,
        workflow_failed_rate_warn: Optional[float] = None,
        breakage_open_rate_warn: Optional[float] = None,
    ) -> str:
        summary = self.summary(
            window_days=window_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            overlay_cache_hit_rate_warn=overlay_cache_hit_rate_warn,
            overlay_cache_min_requests_warn=overlay_cache_min_requests_warn,
            doc_sync_dead_letter_rate_warn=doc_sync_dead_letter_rate_warn,
            workflow_failed_rate_warn=workflow_failed_rate_warn,
            breakage_open_rate_warn=breakage_open_rate_warn,
        )
        common_labels = {
            "window_days": int(summary.get("window_days") or 0),
            "site_id": site_id,
            "target_object": target_object,
            "template_key": template_key,
        }

        lines: List[str] = [
            "# HELP yuantus_parallel_doc_sync_jobs_total Document sync jobs in selected window.",
            "# TYPE yuantus_parallel_doc_sync_jobs_total gauge",
            self._prometheus_line(
                "yuantus_parallel_doc_sync_jobs_total",
                summary.get("doc_sync", {}).get("total"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_doc_sync_dead_letter_total Doc sync dead-letter jobs in selected window.",
            "# TYPE yuantus_parallel_doc_sync_dead_letter_total gauge",
            self._prometheus_line(
                "yuantus_parallel_doc_sync_dead_letter_total",
                summary.get("doc_sync", {}).get("dead_letter_total"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_doc_sync_success_rate Doc sync success rate in selected window.",
            "# TYPE yuantus_parallel_doc_sync_success_rate gauge",
            self._prometheus_line(
                "yuantus_parallel_doc_sync_success_rate",
                summary.get("doc_sync", {}).get("success_rate"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_workflow_runs_total Workflow custom action runs in selected window.",
            "# TYPE yuantus_parallel_workflow_runs_total gauge",
            self._prometheus_line(
                "yuantus_parallel_workflow_runs_total",
                summary.get("workflow_actions", {}).get("total"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_workflow_failed_rate Workflow custom action failed rate in selected window.",
            "# TYPE yuantus_parallel_workflow_failed_rate gauge",
            self._prometheus_line(
                "yuantus_parallel_workflow_failed_rate",
                summary.get("workflow_actions", {}).get("failed_rate"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_breakage_total Breakage incidents in selected window.",
            "# TYPE yuantus_parallel_breakage_total gauge",
            self._prometheus_line(
                "yuantus_parallel_breakage_total",
                summary.get("breakages", {}).get("total"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_breakage_open_total Open breakage incidents in selected window.",
            "# TYPE yuantus_parallel_breakage_open_total gauge",
            self._prometheus_line(
                "yuantus_parallel_breakage_open_total",
                summary.get("breakages", {}).get("open_total"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_consumption_template_versions_total Consumption template versions tracked.",
            "# TYPE yuantus_parallel_consumption_template_versions_total gauge",
            self._prometheus_line(
                "yuantus_parallel_consumption_template_versions_total",
                summary.get("consumption_templates", {}).get("versions_total"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_overlay_cache_requests Overlay cache requests in current process.",
            "# TYPE yuantus_parallel_overlay_cache_requests gauge",
            self._prometheus_line(
                "yuantus_parallel_overlay_cache_requests",
                summary.get("overlay_cache", {}).get("requests"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_overlay_cache_hit_rate Overlay cache hit rate in current process.",
            "# TYPE yuantus_parallel_overlay_cache_hit_rate gauge",
            self._prometheus_line(
                "yuantus_parallel_overlay_cache_hit_rate",
                summary.get("overlay_cache", {}).get("hit_rate"),
                labels=common_labels,
            ),
            "# HELP yuantus_parallel_slo_hints_total Number of active SLO warning hints.",
            "# TYPE yuantus_parallel_slo_hints_total gauge",
            self._prometheus_line(
                "yuantus_parallel_slo_hints_total",
                len(summary.get("slo_hints") or []),
                labels=common_labels,
            ),
        ]

        by_status = summary.get("doc_sync", {}).get("by_status") or {}
        for status, count in sorted(by_status.items()):
            labels = {**common_labels, "status": status}
            lines.append(
                self._prometheus_line(
                    "yuantus_parallel_doc_sync_by_status",
                    count,
                    labels=labels,
                )
            )

        by_result_code = summary.get("workflow_actions", {}).get("by_result_code") or {}
        for result_code, count in sorted(by_result_code.items()):
            labels = {**common_labels, "result_code": result_code}
            lines.append(
                self._prometheus_line(
                    "yuantus_parallel_workflow_by_result_code",
                    count,
                    labels=labels,
                )
            )

        return "\n".join(lines) + "\n"

    def alerts(
        self,
        *,
        window_days: int = 7,
        site_id: Optional[str] = None,
        target_object: Optional[str] = None,
        template_key: Optional[str] = None,
        level: Optional[str] = None,
        overlay_cache_hit_rate_warn: Optional[float] = None,
        overlay_cache_min_requests_warn: Optional[int] = None,
        doc_sync_dead_letter_rate_warn: Optional[float] = None,
        workflow_failed_rate_warn: Optional[float] = None,
        breakage_open_rate_warn: Optional[float] = None,
    ) -> Dict[str, Any]:
        normalized_level = str(level or "").strip().lower() or None
        if normalized_level and normalized_level not in {"warn", "critical", "info"}:
            raise ValueError("level must be one of: warn, critical, info")

        summary = self.summary(
            window_days=window_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            overlay_cache_hit_rate_warn=overlay_cache_hit_rate_warn,
            overlay_cache_min_requests_warn=overlay_cache_min_requests_warn,
            doc_sync_dead_letter_rate_warn=doc_sync_dead_letter_rate_warn,
            workflow_failed_rate_warn=workflow_failed_rate_warn,
            breakage_open_rate_warn=breakage_open_rate_warn,
        )
        hints = summary.get("slo_hints") or []
        if normalized_level:
            hints = [
                row
                for row in hints
                if str((row or {}).get("level") or "").strip().lower() == normalized_level
            ]

        code_counter = Counter(str((row or {}).get("code") or "unknown") for row in hints)
        return {
            "generated_at": summary.get("generated_at"),
            "window_days": summary.get("window_days"),
            "window_since": summary.get("window_since"),
            "filters": {
                "site_id": site_id,
                "target_object": target_object,
                "template_key": template_key,
                "level": normalized_level,
            },
            "slo_thresholds": summary.get("slo_thresholds") or {},
            "status": "warning" if hints else "ok",
            "total": len(hints),
            "by_code": dict(code_counter),
            "hints": hints,
        }

    def _summary_export_rows(self, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        def push(metric: str, value: Any) -> None:
            rows.append({"metric": metric, "value": value})

        push("window_days", summary.get("window_days"))
        push("doc_sync.total", (summary.get("doc_sync") or {}).get("total"))
        push(
            "doc_sync.dead_letter_total",
            (summary.get("doc_sync") or {}).get("dead_letter_total"),
        )
        push(
            "doc_sync.success_rate",
            (summary.get("doc_sync") or {}).get("success_rate"),
        )
        push(
            "workflow_actions.total",
            (summary.get("workflow_actions") or {}).get("total"),
        )
        push(
            "workflow_actions.failed_rate",
            (summary.get("workflow_actions") or {}).get("failed_rate"),
        )
        push("breakages.total", (summary.get("breakages") or {}).get("total"))
        push("breakages.open_total", (summary.get("breakages") or {}).get("open_total"))
        push(
            "consumption_templates.versions_total",
            (summary.get("consumption_templates") or {}).get("versions_total"),
        )
        push(
            "overlay_cache.requests",
            (summary.get("overlay_cache") or {}).get("requests"),
        )
        push(
            "overlay_cache.hit_rate",
            (summary.get("overlay_cache") or {}).get("hit_rate"),
        )
        push("slo_hints.total", len(summary.get("slo_hints") or []))

        for status, count in sorted(((summary.get("doc_sync") or {}).get("by_status") or {}).items()):
            push(f"doc_sync.by_status.{status}", count)
        for code, count in sorted(
            ((summary.get("workflow_actions") or {}).get("by_result_code") or {}).items()
        ):
            push(f"workflow_actions.by_result_code.{code}", count)
        return rows

    def export_summary(
        self,
        *,
        window_days: int = 7,
        site_id: Optional[str] = None,
        target_object: Optional[str] = None,
        template_key: Optional[str] = None,
        export_format: str = "json",
        overlay_cache_hit_rate_warn: Optional[float] = None,
        overlay_cache_min_requests_warn: Optional[int] = None,
        doc_sync_dead_letter_rate_warn: Optional[float] = None,
        workflow_failed_rate_warn: Optional[float] = None,
        breakage_open_rate_warn: Optional[float] = None,
    ) -> Dict[str, Any]:
        summary = self.summary(
            window_days=window_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
            overlay_cache_hit_rate_warn=overlay_cache_hit_rate_warn,
            overlay_cache_min_requests_warn=overlay_cache_min_requests_warn,
            doc_sync_dead_letter_rate_warn=doc_sync_dead_letter_rate_warn,
            workflow_failed_rate_warn=workflow_failed_rate_warn,
            breakage_open_rate_warn=breakage_open_rate_warn,
        )
        normalized = str(export_format or "json").strip().lower()
        if normalized == "json":
            content = json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "content": content,
                "media_type": "application/json",
                "filename": "parallel-ops-summary.json",
            }

        rows = self._summary_export_rows(summary)
        if normalized == "csv":
            csv_io = io.StringIO()
            writer = csv.DictWriter(csv_io, fieldnames=["metric", "value"])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            return {
                "content": csv_io.getvalue().encode("utf-8"),
                "media_type": "text/csv",
                "filename": "parallel-ops-summary.csv",
            }

        if normalized == "md":
            lines = [
                "# Parallel Ops Summary",
                "",
                f"- generated_at: {summary.get('generated_at') or ''}",
                f"- window_days: {summary.get('window_days') or ''}",
                f"- window_since: {summary.get('window_since') or ''}",
                "",
                "| Metric | Value |",
                "| --- | --- |",
            ]
            for row in rows:
                lines.append(f"| {row['metric']} | {row['value']} |")
            return {
                "content": ("\n".join(lines) + "\n").encode("utf-8"),
                "media_type": "text/markdown",
                "filename": "parallel-ops-summary.md",
            }

        raise ValueError("export_format must be json, csv or md")

    def _trend_export_rows(self, trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for row in trends.get("points") or []:
            if not isinstance(row, dict):
                continue
            doc_sync = row.get("doc_sync") if isinstance(row.get("doc_sync"), dict) else {}
            workflow = (
                row.get("workflow_actions")
                if isinstance(row.get("workflow_actions"), dict)
                else {}
            )
            breakages = row.get("breakages") if isinstance(row.get("breakages"), dict) else {}
            rows.append(
                {
                    "bucket_start": row.get("bucket_start"),
                    "bucket_end": row.get("bucket_end"),
                    "doc_sync_total": doc_sync.get("total"),
                    "doc_sync_failed_total": doc_sync.get("failed_total"),
                    "doc_sync_dead_letter_total": doc_sync.get("dead_letter_total"),
                    "doc_sync_success_rate": doc_sync.get("success_rate"),
                    "doc_sync_dead_letter_rate": doc_sync.get("dead_letter_rate"),
                    "workflow_total": workflow.get("total"),
                    "workflow_failed_total": workflow.get("failed_total"),
                    "workflow_failed_rate": workflow.get("failed_rate"),
                    "breakages_total": breakages.get("total"),
                    "breakages_open_total": breakages.get("open_total"),
                    "breakages_open_rate": breakages.get("open_rate"),
                }
            )
        return rows

    def export_trends(
        self,
        *,
        window_days: int = 7,
        bucket_days: int = 1,
        site_id: Optional[str] = None,
        target_object: Optional[str] = None,
        template_key: Optional[str] = None,
        export_format: str = "json",
    ) -> Dict[str, Any]:
        trends = self.trends(
            window_days=window_days,
            bucket_days=bucket_days,
            site_id=site_id,
            target_object=target_object,
            template_key=template_key,
        )
        normalized = str(export_format or "json").strip().lower()
        if normalized == "json":
            content = json.dumps(trends, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "content": content,
                "media_type": "application/json",
                "filename": "parallel-ops-trends.json",
            }

        rows = self._trend_export_rows(trends)
        if normalized == "csv":
            csv_io = io.StringIO()
            writer = csv.DictWriter(
                csv_io,
                fieldnames=[
                    "bucket_start",
                    "bucket_end",
                    "doc_sync_total",
                    "doc_sync_failed_total",
                    "doc_sync_dead_letter_total",
                    "doc_sync_success_rate",
                    "doc_sync_dead_letter_rate",
                    "workflow_total",
                    "workflow_failed_total",
                    "workflow_failed_rate",
                    "breakages_total",
                    "breakages_open_total",
                    "breakages_open_rate",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            return {
                "content": csv_io.getvalue().encode("utf-8"),
                "media_type": "text/csv",
                "filename": "parallel-ops-trends.csv",
            }

        if normalized == "md":
            lines = [
                "# Parallel Ops Trends",
                "",
                f"- generated_at: {trends.get('generated_at') or ''}",
                f"- window_days: {trends.get('window_days') or ''}",
                f"- bucket_days: {trends.get('bucket_days') or ''}",
                f"- window_since: {trends.get('window_since') or ''}",
                "",
                "| Bucket Start | Bucket End | DocSync Total | DocSync Failed | DocSync DeadLetter | Workflow Total | Workflow Failed | Breakages Total | Breakages Open |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
            for row in rows:
                lines.append(
                    "| "
                    f"{row['bucket_start']} | "
                    f"{row['bucket_end']} | "
                    f"{row['doc_sync_total']} | "
                    f"{row['doc_sync_failed_total']} | "
                    f"{row['doc_sync_dead_letter_total']} | "
                    f"{row['workflow_total']} | "
                    f"{row['workflow_failed_total']} | "
                    f"{row['breakages_total']} | "
                    f"{row['breakages_open_total']} |"
                )
            return {
                "content": ("\n".join(lines) + "\n").encode("utf-8"),
                "media_type": "text/markdown",
                "filename": "parallel-ops-trends.md",
            }

        raise ValueError("export_format must be json, csv or md")
