from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.parallel_tasks import BreakageIncident
from yuantus.meta_engine.services.parallel_tasks_service import BreakageIncidentService
from yuantus.meta_engine.tasks.breakage_tasks import (
    breakage_helpdesk_sync_stub,
    breakage_incidents_export,
    breakage_incidents_export_cleanup,
)
from yuantus.models.base import Base
from yuantus.security.rbac.models import RBACUser


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            RBACUser.__table__,
            BreakageIncident.__table__,
            ConversionJob.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()


def test_breakage_helpdesk_sync_stub_task_processes_job() -> None:
    session = _session()
    try:
        service = BreakageIncidentService(session)
        incident = service.create_incident(
            description="task-helpdesk",
            product_item_id="p-task-1",
            bom_line_item_id="bom-task-1",
        )
        session.commit()
        job = service.enqueue_helpdesk_stub_sync(
            incident.id,
            user_id=7,
            provider="jira",
            metadata_json={"channel": "worker"},
        )
        session.commit()

        result = breakage_helpdesk_sync_stub(job.payload, session, job.id)
        session.commit()

        assert result["incident_id"] == incident.id
        assert result["sync_status"] == "completed"
        assert str(result["external_ticket_id"]).startswith("JIRA-")
    finally:
        session.close()


def test_breakage_export_and_cleanup_tasks_process_job_payloads() -> None:
    session = _session()
    try:
        service = BreakageIncidentService(session)
        service.create_incident(
            description="task-export",
            product_item_id="p-task-exp-1",
            bom_line_item_id="bom-task-exp-1",
        )
        session.commit()
        enqueued = service.enqueue_incidents_export_job(
            bom_line_item_id="bom-task-exp-1",
            page=1,
            page_size=20,
            export_format="json",
            execute_immediately=False,
            user_id=9,
        )
        session.commit()

        export_result = breakage_incidents_export(
            {"user_id": 9},
            session,
            enqueued["job_id"],
        )
        session.commit()
        assert export_result["status"] == "completed"
        assert export_result["download_ready"] is True

        job = session.get(ConversionJob, enqueued["job_id"])
        assert job is not None
        job.completed_at = datetime.utcnow() - timedelta(hours=25)
        session.add(job)
        session.commit()

        cleanup_result = breakage_incidents_export_cleanup(
            {"ttl_hours": 24, "limit": 50, "user_id": 9},
            session,
            None,
        )
        session.commit()
        assert cleanup_result["expired_jobs"] >= 1

        status = service.get_incidents_export_job(str(enqueued["job_id"]))
        assert status["download_ready"] is False
        assert status["sync_status"] == "expired"
    finally:
        session.close()
