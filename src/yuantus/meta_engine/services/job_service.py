"""
Job Service
Manages the lifecycle of asynchronous jobs.
Phase 4: Conversion Orchestration
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import asc
from yuantus.meta_engine.models.job import ConversionJob, JobStatus


class JobService:
    def __init__(self, session: Session):
        self.session = session

    def create_job(
        self,
        task_type: str,
        payload: Dict[str, Any],
        user_id: int = None,
        priority: int = 10,
    ) -> ConversionJob:
        """Submit a new background job."""
        job = ConversionJob(
            task_type=task_type,
            payload=payload,
            created_by_id=user_id,
            status=JobStatus.PENDING.value,
            priority=priority,
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

    def fail_job(self, job_id: str, error_message: str):
        """Mark a job as failed, potentially scheduling a retry."""
        job = self.session.get(ConversionJob, job_id)
        if job:
            job.last_error = str(error_message)

            if job.attempt_count < job.max_attempts:
                # Retry logic: Move back to pending
                job.status = JobStatus.PENDING.value
                # Simple backoff: retry immediately or add time to scheduled_at
                # For now, immediate retry availability
            else:
                # Max attempts reached, permanent failure
                job.status = JobStatus.FAILED.value
                job.completed_at = datetime.utcnow()

            self.session.add(job)
            self.session.commit()

    def get_job(self, job_id: str) -> Optional[ConversionJob]:
        return self.session.get(ConversionJob, job_id)
