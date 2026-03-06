from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.services.parallel_tasks_service import (
    BreakageIncidentService,
    ParallelOpsOverviewService,
)


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def breakage_helpdesk_sync_stub(
    payload: Dict[str, Any],
    session: Session,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_job_id = str(job_id or payload.get("job_id") or "").strip()
    if not resolved_job_id:
        raise ValueError("breakage helpdesk task requires job_id")
    service = BreakageIncidentService(session)
    return service.run_helpdesk_sync_job(
        resolved_job_id,
        user_id=_as_int(payload.get("user_id")),
    )


def breakage_incidents_export(
    payload: Dict[str, Any],
    session: Session,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_job_id = str(job_id or payload.get("job_id") or "").strip()
    if not resolved_job_id:
        raise ValueError("breakage incidents export task requires job_id")
    service = BreakageIncidentService(session)
    return service.run_incidents_export_job(
        resolved_job_id,
        user_id=_as_int(payload.get("user_id")),
    )


def breakage_incidents_export_cleanup(
    payload: Dict[str, Any],
    session: Session,
    _job_id: Optional[str] = None,
) -> Dict[str, Any]:
    service = BreakageIncidentService(session)
    return service.cleanup_expired_incidents_export_results(
        ttl_hours=payload.get("ttl_hours", 24),
        limit=payload.get("limit", 200),
        user_id=_as_int(payload.get("user_id")),
    )


def parallel_ops_breakage_helpdesk_failures_export(
    payload: Dict[str, Any],
    session: Session,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_job_id = str(job_id or payload.get("job_id") or "").strip()
    if not resolved_job_id:
        raise ValueError("parallel ops breakage helpdesk export task requires job_id")
    service = ParallelOpsOverviewService(session)
    return service.run_breakage_helpdesk_failures_export_job(
        resolved_job_id,
        user_id=_as_int(payload.get("user_id")),
    )
