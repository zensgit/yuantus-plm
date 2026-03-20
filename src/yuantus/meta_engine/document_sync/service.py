"""
DocumentSyncService -- site management, sync jobs, record tracking, and
summary export for the document multi-site sync domain.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.document_sync.models import (
    SiteState,
    SyncDirection,
    SyncJob,
    SyncJobState,
    SyncRecord,
    SyncRecordOutcome,
    SyncSite,
)


# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------

_SITE_TRANSITIONS: Dict[str, List[str]] = {
    SiteState.ACTIVE.value: [SiteState.DISABLED.value, SiteState.ARCHIVED.value],
    SiteState.DISABLED.value: [SiteState.ACTIVE.value, SiteState.ARCHIVED.value],
    SiteState.ARCHIVED.value: [],  # terminal
}

_JOB_TRANSITIONS: Dict[str, List[str]] = {
    SyncJobState.PENDING.value: [
        SyncJobState.RUNNING.value,
        SyncJobState.CANCELLED.value,
    ],
    SyncJobState.RUNNING.value: [
        SyncJobState.COMPLETED.value,
        SyncJobState.FAILED.value,
        SyncJobState.CANCELLED.value,
    ],
    SyncJobState.COMPLETED.value: [],
    SyncJobState.FAILED.value: [],
    SyncJobState.CANCELLED.value: [],
}

# States that qualify a job for the reconciliation queue
_RECONCILIATION_STATES = {SyncJobState.COMPLETED.value, SyncJobState.FAILED.value}


class DocumentSyncService:
    """Domain service for document multi-site sync management."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Site CRUD
    # ------------------------------------------------------------------

    def create_site(
        self,
        *,
        name: str,
        site_code: str,
        base_url: Optional[str] = None,
        description: Optional[str] = None,
        direction: str = SyncDirection.PUSH.value,
        is_primary: bool = False,
        properties: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[int] = None,
    ) -> SyncSite:
        valid_dirs = {d.value for d in SyncDirection}
        if direction not in valid_dirs:
            raise ValueError(
                f"Invalid direction '{direction}'. Must be one of: {sorted(valid_dirs)}"
            )

        site = SyncSite(
            id=str(uuid.uuid4()),
            name=name,
            site_code=site_code,
            base_url=base_url,
            description=description,
            state=SiteState.ACTIVE.value,
            direction=direction,
            is_primary=is_primary,
            properties=properties,
            created_by_id=created_by_id,
        )
        self.session.add(site)
        self.session.flush()
        return site

    def get_site(self, site_id: str) -> Optional[SyncSite]:
        return self.session.get(SyncSite, site_id)

    def list_sites(
        self,
        *,
        state: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> List[SyncSite]:
        q = self.session.query(SyncSite)
        if state is not None:
            q = q.filter(SyncSite.state == state)
        if direction is not None:
            q = q.filter(SyncSite.direction == direction)
        return q.order_by(SyncSite.created_at.desc()).all()

    def update_site(self, site_id: str, **fields: Any) -> Optional[SyncSite]:
        site = self.get_site(site_id)
        if site is None:
            return None
        for key, value in fields.items():
            if hasattr(site, key) and key not in ("id", "created_at", "created_by_id"):
                setattr(site, key, value)
        self.session.flush()
        return site

    def transition_site_state(
        self, site_id: str, target_state: str
    ) -> SyncSite:
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        allowed = _SITE_TRANSITIONS.get(site.state, [])
        if target_state not in allowed:
            raise ValueError(
                f"Cannot transition site from '{site.state}' to '{target_state}'. "
                f"Allowed: {allowed}"
            )
        site.state = target_state
        self.session.flush()
        return site

    # ------------------------------------------------------------------
    # Job CRUD
    # ------------------------------------------------------------------

    def create_job(
        self,
        *,
        site_id: str,
        direction: str = SyncDirection.PUSH.value,
        document_filter: Optional[Dict[str, Any]] = None,
        properties: Optional[Dict[str, Any]] = None,
        created_by_id: Optional[int] = None,
    ) -> SyncJob:
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")
        if site.state != SiteState.ACTIVE.value:
            raise ValueError(
                f"Cannot create job for site in state '{site.state}'"
            )

        valid_dirs = {d.value for d in SyncDirection}
        if direction not in valid_dirs:
            raise ValueError(
                f"Invalid direction '{direction}'. Must be one of: {sorted(valid_dirs)}"
            )

        job = SyncJob(
            id=str(uuid.uuid4()),
            site_id=site_id,
            state=SyncJobState.PENDING.value,
            direction=direction,
            document_filter=document_filter,
            properties=properties,
            created_by_id=created_by_id,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get_job(self, job_id: str) -> Optional[SyncJob]:
        return self.session.get(SyncJob, job_id)

    def list_jobs(
        self,
        *,
        site_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[SyncJob]:
        q = self.session.query(SyncJob)
        if site_id is not None:
            q = q.filter(SyncJob.site_id == site_id)
        if state is not None:
            q = q.filter(SyncJob.state == state)
        return q.order_by(SyncJob.created_at.desc()).all()

    def transition_job_state(
        self, job_id: str, target_state: str
    ) -> SyncJob:
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        allowed = _JOB_TRANSITIONS.get(job.state, [])
        if target_state not in allowed:
            raise ValueError(
                f"Cannot transition job from '{job.state}' to '{target_state}'. "
                f"Allowed: {allowed}"
            )
        job.state = target_state
        self.session.flush()
        return job

    # ------------------------------------------------------------------
    # Sync records
    # ------------------------------------------------------------------

    def add_record(
        self,
        job_id: str,
        *,
        document_id: str,
        source_checksum: Optional[str] = None,
        target_checksum: Optional[str] = None,
        outcome: str = SyncRecordOutcome.SYNCED.value,
        conflict_detail: Optional[str] = None,
        error_detail: Optional[str] = None,
    ) -> SyncRecord:
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        valid_outcomes = {o.value for o in SyncRecordOutcome}
        if outcome not in valid_outcomes:
            raise ValueError(
                f"Invalid outcome '{outcome}'. Must be one of: {sorted(valid_outcomes)}"
            )

        record = SyncRecord(
            id=str(uuid.uuid4()),
            job_id=job_id,
            document_id=document_id,
            source_checksum=source_checksum,
            target_checksum=target_checksum,
            outcome=outcome,
            conflict_detail=conflict_detail,
            error_detail=error_detail,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_records(self, job_id: str) -> List[SyncRecord]:
        return (
            self.session.query(SyncRecord)
            .filter(SyncRecord.job_id == job_id)
            .order_by(SyncRecord.created_at)
            .all()
        )

    # ------------------------------------------------------------------
    # Summary / export
    # ------------------------------------------------------------------

    def job_summary(self, job_id: str) -> Dict[str, Any]:
        """Build a sync summary payload for downstream export."""
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        records = self.list_records(job_id)

        by_outcome: Dict[str, int] = {}
        conflicts: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for r in records:
            by_outcome[r.outcome] = by_outcome.get(r.outcome, 0) + 1
            if r.outcome == SyncRecordOutcome.CONFLICT.value:
                conflicts.append(
                    {
                        "document_id": r.document_id,
                        "source_checksum": r.source_checksum,
                        "target_checksum": r.target_checksum,
                        "detail": r.conflict_detail,
                    }
                )
            elif r.outcome == SyncRecordOutcome.ERROR.value:
                errors.append(
                    {
                        "document_id": r.document_id,
                        "detail": r.error_detail,
                    }
                )

        return {
            "job_id": job.id,
            "site_id": job.site_id,
            "state": job.state,
            "direction": job.direction,
            "total_records": len(records),
            "by_outcome": by_outcome,
            "conflicts": conflicts,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Analytics (C21)
    # ------------------------------------------------------------------

    def overview(self) -> Dict[str, Any]:
        """High-level overview: site/job counts, state breakdowns."""
        sites = self.session.query(SyncSite).all()
        jobs = self.session.query(SyncJob).all()

        sites_by_state: Dict[str, int] = {}
        sites_by_direction: Dict[str, int] = {}
        for s in sites:
            sites_by_state[s.state] = sites_by_state.get(s.state, 0) + 1
            sites_by_direction[s.direction] = sites_by_direction.get(s.direction, 0) + 1

        jobs_by_state: Dict[str, int] = {}
        total_conflicts = 0
        total_errors = 0
        for j in jobs:
            jobs_by_state[j.state] = jobs_by_state.get(j.state, 0) + 1
            total_conflicts += (j.conflict_count or 0)
            total_errors += (j.error_count or 0)

        return {
            "total_sites": len(sites),
            "sites_by_state": sites_by_state,
            "sites_by_direction": sites_by_direction,
            "total_jobs": len(jobs),
            "jobs_by_state": jobs_by_state,
            "total_conflicts": total_conflicts,
            "total_errors": total_errors,
        }

    def site_analytics(self, site_id: str) -> Dict[str, Any]:
        """Per-site analytics: job counts and outcome aggregates."""
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        jobs = (
            self.session.query(SyncJob)
            .filter(SyncJob.site_id == site_id)
            .all()
        )

        by_state: Dict[str, int] = {}
        total_synced = 0
        total_conflicts = 0
        total_errors = 0
        total_skipped = 0
        for j in jobs:
            by_state[j.state] = by_state.get(j.state, 0) + 1
            total_synced += (j.synced_count or 0)
            total_conflicts += (j.conflict_count or 0)
            total_errors += (j.error_count or 0)
            total_skipped += (j.skipped_count or 0)

        return {
            "site_id": site.id,
            "site_name": site.name,
            "state": site.state,
            "total_jobs": len(jobs),
            "jobs_by_state": by_state,
            "total_synced": total_synced,
            "total_conflicts": total_conflicts,
            "total_errors": total_errors,
            "total_skipped": total_skipped,
        }

    def job_conflicts(self, job_id: str) -> Dict[str, Any]:
        """Conflict-only summary for a specific job."""
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        records = self.list_records(job_id)
        conflicts: List[Dict[str, Any]] = []
        for r in records:
            if r.outcome == SyncRecordOutcome.CONFLICT.value:
                conflicts.append({
                    "document_id": r.document_id,
                    "source_checksum": r.source_checksum,
                    "target_checksum": r.target_checksum,
                    "detail": r.conflict_detail,
                })

        return {
            "job_id": job.id,
            "site_id": job.site_id,
            "total_records": len(records),
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
        }

    def export_overview(self) -> Dict[str, Any]:
        """Export-ready combined overview payload."""
        return {
            "overview": self.overview(),
        }

    def export_conflicts(self) -> Dict[str, Any]:
        """Export-ready conflict summary across all jobs."""
        jobs = self.session.query(SyncJob).all()
        all_conflicts: List[Dict[str, Any]] = []

        for j in jobs:
            records = self.list_records(j.id)
            for r in records:
                if r.outcome == SyncRecordOutcome.CONFLICT.value:
                    all_conflicts.append({
                        "job_id": j.id,
                        "site_id": j.site_id,
                        "document_id": r.document_id,
                        "source_checksum": r.source_checksum,
                        "target_checksum": r.target_checksum,
                        "detail": r.conflict_detail,
                    })

        return {
            "total_conflicts": len(all_conflicts),
            "conflicts": all_conflicts,
        }

    # ------------------------------------------------------------------
    # Reconciliation (C24)
    # ------------------------------------------------------------------

    def reconciliation_queue(self) -> Dict[str, Any]:
        """List all jobs with unresolved conflicts (completed/failed with conflict_count > 0)."""
        all_jobs = self.session.query(SyncJob).all()

        queue_jobs: List[Dict[str, Any]] = []
        for j in all_jobs:
            if (
                j.state in _RECONCILIATION_STATES
                and (j.conflict_count or 0) > 0
            ):
                queue_jobs.append({
                    "job_id": j.id,
                    "site_id": j.site_id,
                    "state": j.state,
                    "conflict_count": j.conflict_count or 0,
                    "error_count": j.error_count or 0,
                })

        return {
            "total_jobs_with_conflicts": len(queue_jobs),
            "jobs": queue_jobs,
        }

    def conflict_resolution_summary(self, job_id: str) -> Dict[str, Any]:
        """Detailed conflict breakdown for a job, including record-level detail."""
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        records = self.list_records(job_id)

        synced = 0
        conflicts = 0
        errors = 0
        skipped = 0
        conflict_details: List[Dict[str, Any]] = []
        error_details: List[Dict[str, Any]] = []

        for r in records:
            if r.outcome == SyncRecordOutcome.SYNCED.value:
                synced += 1
            elif r.outcome == SyncRecordOutcome.CONFLICT.value:
                conflicts += 1
                conflict_details.append({
                    "record_id": r.id,
                    "document_id": r.document_id,
                    "source_checksum": r.source_checksum,
                    "target_checksum": r.target_checksum,
                    "detail": r.conflict_detail,
                })
            elif r.outcome == SyncRecordOutcome.ERROR.value:
                errors += 1
                error_details.append({
                    "record_id": r.id,
                    "document_id": r.document_id,
                    "detail": r.error_detail,
                })
            elif r.outcome == SyncRecordOutcome.SKIPPED.value:
                skipped += 1

        return {
            "job_id": job.id,
            "site_id": job.site_id,
            "state": job.state,
            "total_records": len(records),
            "synced": synced,
            "conflicts": conflicts,
            "errors": errors,
            "skipped": skipped,
            "conflict_details": conflict_details,
            "error_details": error_details,
        }

    def site_reconciliation_status(self, site_id: str) -> Dict[str, Any]:
        """Per-site reconciliation status showing all jobs needing attention."""
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        jobs = (
            self.session.query(SyncJob)
            .filter(SyncJob.site_id == site_id)
            .all()
        )

        jobs_with_conflicts = 0
        jobs_with_errors = 0
        total_unresolved_conflicts = 0
        total_unresolved_errors = 0

        for j in jobs:
            conflict_count = j.conflict_count or 0
            error_count = j.error_count or 0
            if conflict_count > 0:
                jobs_with_conflicts += 1
                total_unresolved_conflicts += conflict_count
            if error_count > 0:
                jobs_with_errors += 1
                total_unresolved_errors += error_count

        return {
            "site_id": site.id,
            "site_name": site.name,
            "state": site.state,
            "total_jobs": len(jobs),
            "jobs_with_conflicts": jobs_with_conflicts,
            "jobs_with_errors": jobs_with_errors,
            "total_unresolved_conflicts": total_unresolved_conflicts,
            "total_unresolved_errors": total_unresolved_errors,
        }

    def export_reconciliation(self) -> Dict[str, Any]:
        """Export-ready reconciliation payload: queue + per-site breakdown."""
        sites = self.session.query(SyncSite).all()
        return {
            "reconciliation_queue": self.reconciliation_queue(),
            "sites": [self.site_reconciliation_status(s.id) for s in sites],
        }

    # ------------------------------------------------------------------
    # Replay / audit (C27)
    # ------------------------------------------------------------------

    def replay_overview(self) -> Dict[str, Any]:
        """Fleet-wide replay/retry statistics: retryable, replayable job counts."""
        jobs = self.session.query(SyncJob).all()

        by_state: Dict[str, int] = {}
        retryable = 0  # failed jobs that could be retried
        replay_candidates = 0  # completed jobs with errors/conflicts
        total_synced = 0
        total_documents = 0

        for j in jobs:
            by_state[j.state] = by_state.get(j.state, 0) + 1
            total_synced += (j.synced_count or 0)
            total_documents += (j.total_documents or 0)

            if j.state == SyncJobState.FAILED.value:
                retryable += 1
            elif j.state == SyncJobState.COMPLETED.value:
                if (j.error_count or 0) > 0 or (j.conflict_count or 0) > 0:
                    replay_candidates += 1

        return {
            "total_jobs": len(jobs),
            "by_state": by_state,
            "retryable": retryable,
            "replay_candidates": replay_candidates,
            "total_synced": total_synced,
            "total_documents": total_documents,
        }

    def site_audit(self, site_id: str) -> Dict[str, Any]:
        """Per-site audit: job outcome ratios and health score."""
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        jobs = (
            self.session.query(SyncJob)
            .filter(SyncJob.site_id == site_id)
            .all()
        )

        completed = 0
        failed = 0
        cancelled = 0
        total_synced = 0
        total_conflicts = 0
        total_errors = 0

        for j in jobs:
            if j.state == SyncJobState.COMPLETED.value:
                completed += 1
            elif j.state == SyncJobState.FAILED.value:
                failed += 1
            elif j.state == SyncJobState.CANCELLED.value:
                cancelled += 1
            total_synced += (j.synced_count or 0)
            total_conflicts += (j.conflict_count or 0)
            total_errors += (j.error_count or 0)

        finished = completed + failed
        health_pct = round(
            completed / finished * 100, 1
        ) if finished > 0 else 100.0

        return {
            "site_id": site.id,
            "site_name": site.name,
            "state": site.state,
            "total_jobs": len(jobs),
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "total_synced": total_synced,
            "total_conflicts": total_conflicts,
            "total_errors": total_errors,
            "health_pct": health_pct,
        }

    def job_audit(self, job_id: str) -> Dict[str, Any]:
        """Per-job audit: record-level outcome breakdown and data integrity checks."""
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        records = self.list_records(job_id)

        by_outcome: Dict[str, int] = {}
        checksum_mismatches = 0
        missing_checksums = 0

        for r in records:
            by_outcome[r.outcome] = by_outcome.get(r.outcome, 0) + 1
            if r.source_checksum and r.target_checksum:
                if r.source_checksum != r.target_checksum:
                    checksum_mismatches += 1
            elif r.source_checksum is None and r.target_checksum is None:
                missing_checksums += 1

        is_retryable = job.state == SyncJobState.FAILED.value
        has_issues = (
            (job.error_count or 0) > 0 or (job.conflict_count or 0) > 0
        )

        return {
            "job_id": job.id,
            "site_id": job.site_id,
            "state": job.state,
            "direction": job.direction,
            "total_records": len(records),
            "by_outcome": by_outcome,
            "checksum_mismatches": checksum_mismatches,
            "missing_checksums": missing_checksums,
            "is_retryable": is_retryable,
            "has_issues": has_issues,
        }

    def export_audit(self) -> Dict[str, Any]:
        """Export-ready audit payload: replay overview + per-site audit."""
        sites = self.session.query(SyncSite).all()
        return {
            "replay_overview": self.replay_overview(),
            "sites": [self.site_audit(s.id) for s in sites],
        }

    # ------------------------------------------------------------------
    # Drift / Snapshots (C30)
    # ------------------------------------------------------------------

    def drift_overview(self) -> Dict[str, Any]:
        """Fleet-wide drift metrics: issue rates and conflict/sync totals."""
        sites = self.session.query(SyncSite).all()
        jobs = self.session.query(SyncJob).all()

        jobs_with_issues = 0
        sites_with_failed: set = set()
        total_synced_documents = 0
        total_conflicts = 0

        for j in jobs:
            error_count = j.error_count or 0
            conflict_count = j.conflict_count or 0
            if error_count > 0 or conflict_count > 0:
                jobs_with_issues += 1
            if j.state == SyncJobState.FAILED.value:
                sites_with_failed.add(j.site_id)
            total_synced_documents += (j.synced_count or 0)
            total_conflicts += conflict_count

        total_jobs = len(jobs)
        drift_rate: Any = (
            round(jobs_with_issues / total_jobs * 100, 1)
            if total_jobs > 0
            else None
        )

        return {
            "total_sites": len(sites),
            "total_jobs": total_jobs,
            "jobs_with_issues": jobs_with_issues,
            "drift_rate": drift_rate,
            "sites_with_failed_jobs": len(sites_with_failed),
            "total_synced_documents": total_synced_documents,
            "total_conflicts": total_conflicts,
        }

    def site_snapshots(self, site_id: str) -> Dict[str, Any]:
        """Per-site snapshot: job health, sync totals, and latest job state."""
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        jobs = (
            self.session.query(SyncJob)
            .filter(SyncJob.site_id == site_id)
            .all()
        )

        total = len(jobs)
        completed = 0
        total_synced = 0
        total_errors = 0
        total_conflicts = 0
        latest_job_state: Any = None

        for j in jobs:
            if j.state == SyncJobState.COMPLETED.value:
                completed += 1
            total_synced += (j.synced_count or 0)
            total_errors += (j.error_count or 0)
            total_conflicts += (j.conflict_count or 0)
            latest_job_state = j.state  # last in list (ordered by created_at desc)

        health_pct: Any = (
            round(completed / total * 100, 1)
            if total > 0
            else None
        )

        return {
            "site_id": site.id,
            "site_name": site.name,
            "state": site.state,
            "direction": site.direction,
            "total_jobs": total,
            "latest_job_state": latest_job_state,
            "completed_jobs": completed,
            "total_synced": total_synced,
            "total_errors": total_errors,
            "total_conflicts": total_conflicts,
            "health_pct": health_pct,
        }

    def job_drift(self, job_id: str) -> Dict[str, Any]:
        """Per-job drift detail: completeness, issue detection, record breakdown."""
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        total_documents = job.total_documents or 0
        synced_count = job.synced_count or 0
        conflict_count = job.conflict_count or 0
        error_count = job.error_count or 0
        skipped_count = job.skipped_count or 0

        drift_detected = error_count > 0 or conflict_count > 0

        sync_completeness_pct: Any = (
            round(synced_count / total_documents * 100, 1)
            if total_documents > 0
            else None
        )

        records = self.list_records(job_id)
        records_by_outcome: Dict[str, int] = {}
        for r in records:
            records_by_outcome[r.outcome] = records_by_outcome.get(r.outcome, 0) + 1

        return {
            "job_id": job.id,
            "state": job.state,
            "direction": job.direction,
            "total_documents": total_documents,
            "synced_count": synced_count,
            "conflict_count": conflict_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "drift_detected": drift_detected,
            "sync_completeness_pct": sync_completeness_pct,
            "records_by_outcome": records_by_outcome,
        }

    def export_drift(self) -> Dict[str, Any]:
        """Export-ready drift payload: overview + per-site snapshots."""
        sites = self.session.query(SyncSite).all()
        return {
            "drift_overview": self.drift_overview(),
            "sites": [self.site_snapshots(s.id) for s in sites],
        }

    # ------------------------------------------------------------------
    # Baseline / Lineage (C33)
    # ------------------------------------------------------------------

    def baseline_overview(self) -> Dict[str, Any]:
        """Fleet-wide baseline metrics: coverage and sync totals."""
        sites = self.session.query(SyncSite).all()
        jobs = self.session.query(SyncJob).all()

        total_records = 0
        baseline_jobs = 0
        sites_with_baseline: set = set()

        for j in jobs:
            total_records += (j.synced_count or 0)
            if j.state == SyncJobState.COMPLETED.value:
                baseline_jobs += 1
                sites_with_baseline.add(j.site_id)

        total_jobs = len(jobs)
        baseline_coverage_pct: Any = (
            round(baseline_jobs / total_jobs * 100, 1)
            if total_jobs > 0
            else None
        )

        return {
            "total_sites": len(sites),
            "total_jobs": total_jobs,
            "total_records": total_records,
            "baseline_jobs": baseline_jobs,
            "baseline_coverage_pct": baseline_coverage_pct,
            "sites_with_baseline": len(sites_with_baseline),
        }

    def site_lineage(self, site_id: str) -> Dict[str, Any]:
        """Per-site lineage: job history and sync aggregates."""
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        jobs = (
            self.session.query(SyncJob)
            .filter(SyncJob.site_id == site_id)
            .all()
        )

        completed = 0
        failed = 0
        cancelled = 0
        total_synced = 0
        total_errors = 0

        for j in jobs:
            if j.state == SyncJobState.COMPLETED.value:
                completed += 1
            elif j.state == SyncJobState.FAILED.value:
                failed += 1
            elif j.state == SyncJobState.CANCELLED.value:
                cancelled += 1
            total_synced += (j.synced_count or 0)
            total_errors += (j.error_count or 0)

        return {
            "site_id": site.id,
            "site_name": site.name,
            "state": site.state,
            "direction": site.direction,
            "total_jobs": len(jobs),
            "completed_jobs": completed,
            "failed_jobs": failed,
            "cancelled_jobs": cancelled,
            "total_synced": total_synced,
            "total_errors": total_errors,
            "lineage_depth": len(jobs),
        }

    def job_snapshot_lineage(self, job_id: str) -> Dict[str, Any]:
        """Per-job snapshot lineage: completeness and record breakdown."""
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job '{job_id}' not found")

        total_documents = job.total_documents or 0
        synced_count = job.synced_count or 0
        conflict_count = job.conflict_count or 0
        error_count = job.error_count or 0
        skipped_count = job.skipped_count or 0

        is_baseline = job.state == SyncJobState.COMPLETED.value

        completeness_pct: Any = (
            round(synced_count / total_documents * 100, 1)
            if total_documents > 0
            else None
        )

        records = self.list_records(job_id)
        records_by_outcome: Dict[str, int] = {}
        for r in records:
            records_by_outcome[r.outcome] = records_by_outcome.get(r.outcome, 0) + 1

        return {
            "job_id": job.id,
            "state": job.state,
            "direction": job.direction,
            "total_documents": total_documents,
            "synced_count": synced_count,
            "conflict_count": conflict_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "is_baseline": is_baseline,
            "records_by_outcome": records_by_outcome,
            "completeness_pct": completeness_pct,
        }

    def export_lineage(self) -> Dict[str, Any]:
        """Export-ready lineage payload: overview + per-site lineage."""
        sites = self.session.query(SyncSite).all()
        return {
            "baseline_overview": self.baseline_overview(),
            "sites": [self.site_lineage(s.id) for s in sites],
        }

    # ------------------------------------------------------------------
    # Checkpoints / Retention (C36)
    # ------------------------------------------------------------------

    def checkpoints_overview(self) -> Dict[str, Any]:
        """Fleet-wide checkpoint metrics: site counts, job completion rates, retention readiness."""
        sites = self.session.query(SyncSite).all()
        jobs = self.session.query(SyncJob).all()

        sites_by_state: Dict[str, int] = {}
        for s in sites:
            sites_by_state[s.state] = sites_by_state.get(s.state, 0) + 1

        total_jobs = len(jobs)
        completed_jobs = 0
        failed_jobs = 0
        total_synced = 0
        total_errors = 0

        for j in jobs:
            if j.state == SyncJobState.COMPLETED.value:
                completed_jobs += 1
            elif j.state == SyncJobState.FAILED.value:
                failed_jobs += 1
            total_synced += (j.synced_count or 0)
            total_errors += (j.error_count or 0)

        completion_rate: Any = (
            round(completed_jobs / total_jobs * 100, 1)
            if total_jobs > 0
            else None
        )

        retention_ready = total_errors == 0 and completed_jobs > 0

        return {
            "total_sites": len(sites),
            "sites_by_state": sites_by_state,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "completion_rate": completion_rate,
            "total_synced": total_synced,
            "total_errors": total_errors,
            "retention_ready": retention_ready,
        }

    def retention_summary(self) -> Dict[str, Any]:
        """Retention summary: record age distribution, conflict/error retention metrics."""
        jobs = self.session.query(SyncJob).all()

        total_records = 0
        synced_records = 0
        conflict_records = 0
        error_records = 0
        skipped_records = 0

        for j in jobs:
            synced_records += (j.synced_count or 0)
            conflict_records += (j.conflict_count or 0)
            error_records += (j.error_count or 0)
            skipped_records += (j.skipped_count or 0)

        total_records = synced_records + conflict_records + error_records + skipped_records

        conflict_retention_pct: Any = (
            round(conflict_records / total_records * 100, 1)
            if total_records > 0
            else None
        )

        error_retention_pct: Any = (
            round(error_records / total_records * 100, 1)
            if total_records > 0
            else None
        )

        clean_sync_pct: Any = (
            round(synced_records / total_records * 100, 1)
            if total_records > 0
            else None
        )

        return {
            "total_records": total_records,
            "synced_records": synced_records,
            "conflict_records": conflict_records,
            "error_records": error_records,
            "skipped_records": skipped_records,
            "conflict_retention_pct": conflict_retention_pct,
            "error_retention_pct": error_retention_pct,
            "clean_sync_pct": clean_sync_pct,
        }

    def site_checkpoints(self, site_id: str) -> Dict[str, Any]:
        """Per-site checkpoint detail: jobs as checkpoints, completion rate, record coverage."""
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        jobs = (
            self.session.query(SyncJob)
            .filter(SyncJob.site_id == site_id)
            .all()
        )

        total = len(jobs)
        completed = 0
        total_synced = 0
        total_errors = 0
        total_conflicts = 0
        checkpoints: List[Dict[str, Any]] = []

        for j in jobs:
            if j.state == SyncJobState.COMPLETED.value:
                completed += 1
            total_synced += (j.synced_count or 0)
            total_errors += (j.error_count or 0)
            total_conflicts += (j.conflict_count or 0)
            checkpoints.append({
                "job_id": j.id,
                "state": j.state,
                "synced_count": j.synced_count or 0,
                "error_count": j.error_count or 0,
                "conflict_count": j.conflict_count or 0,
            })

        completion_rate: Any = (
            round(completed / total * 100, 1)
            if total > 0
            else None
        )

        return {
            "site_id": site.id,
            "site_name": site.name,
            "state": site.state,
            "total_checkpoints": total,
            "completed_checkpoints": completed,
            "completion_rate": completion_rate,
            "total_synced": total_synced,
            "total_errors": total_errors,
            "total_conflicts": total_conflicts,
            "checkpoints": checkpoints,
        }

    def export_retention(self) -> Dict[str, Any]:
        """Export-ready combined checkpoints + retention + per-site details."""
        sites = self.session.query(SyncSite).all()
        return {
            "checkpoints_overview": self.checkpoints_overview(),
            "retention_summary": self.retention_summary(),
            "sites": [self.site_checkpoints(s.id) for s in sites],
        }

    # ------------------------------------------------------------------
    # Freshness / Watermarks helpers (C39)
    # ------------------------------------------------------------------

    def freshness_overview(self) -> Dict[str, Any]:
        """Fleet-wide freshness summary: total sites, sites with stale docs,
        avg freshness score, freshest/stalest sites."""
        sites = self.session.query(SyncSite).all()
        jobs = self.session.query(SyncJob).all()

        # Group jobs by site_id
        jobs_by_site: Dict[str, List[SyncJob]] = {}
        for j in jobs:
            jobs_by_site.setdefault(j.site_id, []).append(j)

        site_freshness_scores: Dict[str, float] = {}
        stale_site_count = 0

        for s in sites:
            site_jobs = jobs_by_site.get(s.id, [])
            total_synced = 0
            total_records = 0
            for j in site_jobs:
                synced = j.synced_count or 0
                conflicts = j.conflict_count or 0
                errors = j.error_count or 0
                skipped = j.skipped_count or 0
                total_synced += synced
                total_records += synced + conflicts + errors + skipped

            freshness_pct = (
                round(total_synced / total_records * 100, 1)
                if total_records > 0
                else None
            )
            site_freshness_scores[s.id] = freshness_pct if freshness_pct is not None else 0.0

            # A site is stale if freshness < 100% (has non-synced records)
            if freshness_pct is not None and freshness_pct < 100.0:
                stale_site_count += 1

        # Average freshness across sites with data
        scores_with_data = [
            v for s_id, v in site_freshness_scores.items()
            if jobs_by_site.get(s_id)
        ]
        avg_freshness_pct: Any = (
            round(sum(scores_with_data) / len(scores_with_data), 1)
            if scores_with_data
            else None
        )

        # Freshest / stalest
        freshest_site_id: Any = None
        stalest_site_id: Any = None
        if scores_with_data:
            freshest_site_id = max(
                (s_id for s_id in site_freshness_scores if jobs_by_site.get(s_id)),
                key=lambda s_id: site_freshness_scores[s_id],
            )
            stalest_site_id = min(
                (s_id for s_id in site_freshness_scores if jobs_by_site.get(s_id)),
                key=lambda s_id: site_freshness_scores[s_id],
            )

        return {
            "total_sites": len(sites),
            "stale_site_count": stale_site_count,
            "avg_freshness_pct": avg_freshness_pct,
            "freshest_site_id": freshest_site_id,
            "stalest_site_id": stalest_site_id,
        }

    def watermarks_summary(self) -> Dict[str, Any]:
        """Watermark summary: high/low watermarks per site based on sync lag,
        sites exceeding watermark threshold."""
        sites = self.session.query(SyncSite).all()
        jobs = self.session.query(SyncJob).all()

        watermark_threshold = 50.0

        # Group jobs by site_id
        jobs_by_site: Dict[str, List[SyncJob]] = {}
        for j in jobs:
            jobs_by_site.setdefault(j.site_id, []).append(j)

        exceeded_count = 0
        site_watermarks: List[Dict[str, Any]] = []

        for s in sites:
            site_jobs = jobs_by_site.get(s.id, [])
            total_synced = 0
            total_records = 0
            for j in site_jobs:
                synced = j.synced_count or 0
                conflicts = j.conflict_count or 0
                errors = j.error_count or 0
                skipped = j.skipped_count or 0
                total_synced += synced
                total_records += synced + conflicts + errors + skipped

            freshness_pct: Any = (
                round(total_synced / total_records * 100, 1)
                if total_records > 0
                else None
            )

            high_watermark = freshness_pct if freshness_pct is not None else 0.0
            low_watermark = round(100.0 - high_watermark, 1)
            exceeded = (
                freshness_pct is not None and freshness_pct < watermark_threshold
            )

            if exceeded:
                exceeded_count += 1

            site_watermarks.append({
                "site_id": s.id,
                "freshness_pct": freshness_pct,
                "high_watermark": high_watermark,
                "low_watermark": low_watermark,
                "exceeded": exceeded,
            })

        return {
            "total_sites": len(sites),
            "exceeded_count": exceeded_count,
            "watermark_threshold": watermark_threshold,
            "site_watermarks": site_watermarks,
        }

    def site_freshness(self, site_id: str) -> Dict[str, Any]:
        """Per-site freshness detail: site info, document freshness metrics,
        stale document count. Raises ValueError if site not found."""
        site = self.get_site(site_id)
        if site is None:
            raise ValueError(f"Site '{site_id}' not found")

        jobs = (
            self.session.query(SyncJob)
            .filter(SyncJob.site_id == site_id)
            .all()
        )

        total_synced = 0
        total_conflicts = 0
        total_errors = 0
        total_skipped = 0

        for j in jobs:
            total_synced += (j.synced_count or 0)
            total_conflicts += (j.conflict_count or 0)
            total_errors += (j.error_count or 0)
            total_skipped += (j.skipped_count or 0)

        total_records = total_synced + total_conflicts + total_errors + total_skipped
        stale_doc_count = total_conflicts + total_errors + total_skipped

        freshness_pct: Any = (
            round(total_synced / total_records * 100, 1)
            if total_records > 0
            else None
        )

        return {
            "site_id": site.id,
            "site_name": site.name,
            "state": site.state,
            "direction": site.direction,
            "total_records": total_records,
            "synced_count": total_synced,
            "stale_doc_count": stale_doc_count,
            "freshness_pct": freshness_pct,
        }

    def export_watermarks(self) -> Dict[str, Any]:
        """Export-ready payload combining freshness_overview, watermarks_summary,
        and per-site freshness details."""
        sites = self.session.query(SyncSite).all()
        return {
            "freshness_overview": self.freshness_overview(),
            "watermarks_summary": self.watermarks_summary(),
            "sites": [self.site_freshness(s.id) for s in sites],
        }
