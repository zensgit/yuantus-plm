"""
Job Service
Manages the lifecycle of asynchronous jobs.
Phase 4: Conversion Orchestration
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import asc
from yuantus.meta_engine.models.job import ConversionJob, JobStatus
from yuantus.config import get_settings


class JobService:
    def __init__(self, session: Session):
        self.session = session

    def create_job(
        self,
        task_type: str,
        payload: Dict[str, Any],
        user_id: int = None,
        priority: int = 10,
        *,
        max_attempts: Optional[int] = None,
        dedupe_key: Optional[str] = None,
        dedupe: bool = False,
    ) -> ConversionJob:
        """Submit a new background job."""
        settings = get_settings()
        resolved_max_attempts = (
            max_attempts
            if max_attempts is not None
            else settings.JOB_MAX_ATTEMPTS_DEFAULT
        )
        if dedupe and not dedupe_key:
            dedupe_key = self._build_dedupe_key(task_type, payload)
        if dedupe_key:
            existing = (
                self.session.query(ConversionJob)
                .filter(
                    ConversionJob.dedupe_key == dedupe_key,
                    ConversionJob.status.in_(
                        [JobStatus.PENDING.value, JobStatus.PROCESSING.value]
                    ),
                )
                .order_by(ConversionJob.created_at.desc())
                .first()
            )
            if existing:
                # cad_dedup_vision: "index=true" is a superset of "index=false".
                # If a request asks for indexing but we dedupe to an existing job, promote the
                # existing job payload so the worker will perform indexing when it runs.
                try:
                    if task_type == "cad_dedup_vision" and isinstance(payload, dict):
                        want_index = bool(payload.get("index", False))
                        if want_index:
                            cur = dict(existing.payload or {}) if isinstance(existing.payload, dict) else {}
                            if not bool(cur.get("index", False)):
                                cur["index"] = True
                                existing.payload = cur
                                self.session.add(existing)
                                self.session.commit()
                except Exception:
                    # Never fail job submission due to promotion; fall back to returning the existing job.
                    pass
                return existing
        self._enforce_quota_for_job(payload)
        job = ConversionJob(
            task_type=task_type,
            payload=payload,
            created_by_id=user_id,
            status=JobStatus.PENDING.value,
            priority=priority,
            max_attempts=resolved_max_attempts,
            dedupe_key=dedupe_key,
        )
        self.session.add(job)
        self.session.commit()
        return job

    def poll_next_job(self, worker_id: str) -> Optional[ConversionJob]:
        """
        Finds the next pending job and locks it for this worker.

        Uses FOR UPDATE SKIP LOCKED on PostgreSQL for concurrent worker safety.
        Falls back to simple query on SQLite (acceptable for low volume dev).
        """
        dialect = self.session.bind.dialect.name if self.session.bind else "unknown"

        query = (
            self.session.query(ConversionJob)
            .filter(
                ConversionJob.status == JobStatus.PENDING.value,
                ConversionJob.scheduled_at <= datetime.utcnow(),
            )
            .order_by(asc(ConversionJob.priority), asc(ConversionJob.created_at))
        )

        # PostgreSQL: Use SKIP LOCKED to prevent race conditions
        if dialect == "postgresql":
            query = query.with_for_update(skip_locked=True)

        if self._processing_limit_reached():
            return None

        job = query.first()

        if job:
            job.status = JobStatus.PROCESSING.value
            job.worker_id = worker_id
            job.started_at = datetime.utcnow()
            job.attempt_count += 1
            self.session.add(job)
            self.session.commit()
            return job
        return None

    def complete_job(self, job_id: str, result: Any = None):
        """Mark a job as successfully completed (optionally persisting result into payload)."""
        job = self.session.get(ConversionJob, job_id)
        if job:
            job.status = JobStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()
            if result is not None:
                payload = dict(job.payload or {})
                payload["result"] = result
                payload["result_at"] = job.completed_at.isoformat()
                job.payload = payload
            self.session.add(job)
            self.session.commit()

    def update_job_progress(
        self,
        job_id: str,
        *,
        stage: str,
        current: int,
        total: int,
        message: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update progress metadata stored in the job payload."""
        job = self.session.get(ConversionJob, job_id)
        if not job:
            return
        payload = dict(job.payload or {})
        progress = payload.get("progress")
        if not isinstance(progress, dict):
            progress = {}
        percent = None
        if total:
            percent = max(0, min(100, int(round(current / total * 100))))
        progress.update(
            {
                "stage": stage,
                "current": current,
                "total": total,
                "percent": percent,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )
        if message:
            progress["message"] = message
        if extra:
            progress["extra"] = extra
        payload["progress"] = progress
        job.payload = payload
        self.session.add(job)
        self.session.commit()

    def fail_job(
        self,
        job_id: str,
        error_message: str,
        *,
        retry: bool = True,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        """Mark a job as failed, potentially scheduling a retry."""
        job = self.session.get(ConversionJob, job_id)
        if job:
            settings = get_settings()
            now = datetime.utcnow()
            job.last_error = str(error_message)
            payload = dict(job.payload or {})
            error_record = {
                "code": error_code or "job_failed",
                "message": str(error_message),
                "at": now.isoformat(),
                "attempt": job.attempt_count,
                "max_attempts": job.max_attempts,
                "retry": bool(retry),
            }
            if error_details:
                error_record["details"] = error_details
            history = payload.get("error_history")
            if not isinstance(history, list):
                history = []
            history.append(error_record)
            payload["error"] = error_record
            payload["error_history"] = history
            job.payload = payload

            if not retry:
                job.status = JobStatus.FAILED.value
                job.completed_at = now
            elif job.attempt_count < job.max_attempts:
                # Retry logic: Move back to pending
                job.status = JobStatus.PENDING.value
                delay = max(settings.JOB_RETRY_BACKOFF_SECONDS, 0)
                if delay:
                    backoff = delay * max(job.attempt_count, 1)
                    job.scheduled_at = now + timedelta(seconds=backoff)
                else:
                    job.scheduled_at = now
                job.worker_id = None
                job.started_at = None
                job.completed_at = None
            else:
                # Max attempts reached, permanent failure
                job.status = JobStatus.FAILED.value
                job.completed_at = now

            if job.status == JobStatus.FAILED.value:
                file_id = payload.get("file_id") if isinstance(payload, dict) else None
                if file_id:
                    try:
                        from yuantus.meta_engine.models.cad_audit import CadChangeLog
                        from yuantus.meta_engine.models.file import (
                            FileContainer,
                            ConversionStatus,
                        )

                        file_container = self.session.get(FileContainer, file_id)
                        if (
                            file_container
                            and job.task_type
                            in {
                                "cad_preview",
                                "cad_geometry",
                                "cad_extract",
                                "cad_bom",
                                "cad_dedup_vision",
                                "cad_ml_vision",
                            }
                        ):
                            file_container.conversion_status = (
                                ConversionStatus.FAILED.value
                            )
                            file_container.conversion_error = str(error_message)
                            self.session.add(file_container)

                        if str(job.task_type or "").startswith("cad_"):
                            self.session.add(
                                CadChangeLog(
                                    file_id=str(file_id),
                                    action="job_failed",
                                    payload={
                                        "job_id": job.id,
                                        "task_type": job.task_type,
                                        "error_code": error_record["code"],
                                        "error_message": error_record["message"],
                                        "attempt": job.attempt_count,
                                        "max_attempts": job.max_attempts,
                                        "retry": error_record["retry"],
                                    },
                                    tenant_id=payload.get("tenant_id"),
                                    org_id=payload.get("org_id"),
                                    user_id=payload.get("user_id") or job.created_by_id,
                                )
                            )
                    except Exception:
                        # Never fail job handling due to audit logging.
                        pass

            self.session.add(job)
            self.session.commit()

    def requeue_stale_jobs(self) -> int:
        """Requeue jobs stuck in PROCESSING beyond the stale timeout."""
        settings = get_settings()
        timeout = settings.JOB_STALE_TIMEOUT_SECONDS
        if timeout <= 0:
            return 0
        cutoff = datetime.utcnow() - timedelta(seconds=timeout)
        stale_jobs = (
            self.session.query(ConversionJob)
            .filter(
                ConversionJob.status == JobStatus.PROCESSING.value,
                ConversionJob.started_at.isnot(None),
                ConversionJob.started_at < cutoff,
            )
            .all()
        )
        if not stale_jobs:
            return 0
        for job in stale_jobs:
            if job.attempt_count < job.max_attempts:
                job.status = JobStatus.PENDING.value
                job.worker_id = None
                job.started_at = None
                job.completed_at = None
                job.last_error = "stale_timeout_requeued"
                delay = max(settings.JOB_RETRY_BACKOFF_SECONDS, 0)
                if delay:
                    backoff = delay * max(job.attempt_count, 1)
                    job.scheduled_at = datetime.utcnow() + timedelta(seconds=backoff)
            else:
                job.status = JobStatus.FAILED.value
                job.completed_at = datetime.utcnow()
                job.last_error = "stale_timeout_failed"
        self.session.add_all(stale_jobs)
        self.session.commit()
        return len(stale_jobs)

    def _build_dedupe_key(self, task_type: str, payload: Dict[str, Any]) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        file_id = payload.get("file_id")
        item_id = payload.get("item_id")
        if file_id:
            suffix = ""
            if task_type == "cad_geometry":
                target_format = payload.get("target_format")
                if target_format:
                    suffix = f":{str(target_format).lower()}"
            if task_type == "cad_dedup_vision":
                mode = payload.get("mode")
                if mode:
                    suffix = f":{str(mode).lower()}"
            return f"{task_type}:file:{file_id}{suffix}"
        if item_id:
            return f"{task_type}:item:{item_id}"
        return None

    def _resolve_tenant_id(self, payload: Dict[str, Any]) -> Optional[str]:
        from yuantus.context import tenant_id_var

        tenant_id = tenant_id_var.get()
        if tenant_id:
            return str(tenant_id)
        if isinstance(payload, dict):
            payload_tenant = payload.get("tenant_id")
            if payload_tenant:
                return str(payload_tenant)
        return None

    def _enforce_quota_for_job(self, payload: Dict[str, Any]) -> None:
        settings = get_settings()
        if settings.QUOTA_MODE != "enforce":
            return

        tenant_id = self._resolve_tenant_id(payload)
        if not tenant_id:
            return

        from yuantus.security.auth.database import get_identity_db_session
        from yuantus.security.auth.quota_service import QuotaService

        with get_identity_db_session() as identity_db:
            quota_service = QuotaService(identity_db, meta_db=self.session)
            quota_service.raise_if_exceeded(tenant_id, deltas={"active_jobs": 1})

    def _processing_limit_reached(self) -> bool:
        settings = get_settings()
        if settings.QUOTA_MODE != "enforce":
            return False

        tenant_id = self._resolve_tenant_id({})
        if not tenant_id:
            return False

        from yuantus.security.auth.database import get_identity_db_session
        from yuantus.security.auth.quota_service import QuotaService

        with get_identity_db_session() as identity_db:
            quota_service = QuotaService(identity_db, meta_db=self.session)
            decisions = quota_service.evaluate(tenant_id, deltas={"processing_jobs": 1})
            return bool(decisions)

    def get_job(self, job_id: str) -> Optional[ConversionJob]:
        return self.session.get(ConversionJob, job_id)
