from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.job import ConversionJob, JobStatus
from yuantus.meta_engine.services.job_service import JobService
from yuantus.models.base import Base
from yuantus.observability.metrics import (
    render_prometheus_text,
    reset_registry,
)


@pytest.fixture()
def session():
    import_all_models()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[ConversionJob.__table__])
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_function(_fn) -> None:
    reset_registry()


def _make_job(session, *, started_offset_ms: int = 1000) -> ConversionJob:
    now = datetime.utcnow()
    job = ConversionJob(
        id="job-1",
        task_type="cad_convert",
        status=JobStatus.PROCESSING.value,
        payload={"file_id": "f1"},
        started_at=now - timedelta(milliseconds=started_offset_ms),
        attempt_count=1,
        max_attempts=3,
    )
    session.add(job)
    session.commit()
    return job


def test_complete_job_records_success_metric(session) -> None:
    _make_job(session, started_offset_ms=300)
    svc = JobService(session)
    svc.complete_job("job-1", result={"ok": True})

    out = render_prometheus_text()
    assert 'yuantus_jobs_total{task_type="cad_convert",status="success"} 1' in out
    assert 'yuantus_job_duration_ms_count{task_type="cad_convert",status="success"} 1' in out


def test_fail_job_terminal_records_failure_metric(session) -> None:
    _make_job(session, started_offset_ms=600)
    svc = JobService(session)
    svc.fail_job("job-1", "boom", retry=False, error_code="fatal")

    out = render_prometheus_text()
    assert 'yuantus_jobs_total{task_type="cad_convert",status="failure"} 1' in out
    assert 'yuantus_job_duration_ms_count{task_type="cad_convert",status="failure"} 1' in out


def test_fail_job_retry_records_retry_metric_with_duration(session) -> None:
    """Regression guard: fail_job's retry branch resets started_at and
    completed_at to None on lines 224-225. The metric must be computed BEFORE
    that reset, otherwise duration is lost on retry-paths."""
    _make_job(session, started_offset_ms=200)
    svc = JobService(session)
    svc.fail_job("job-1", "transient", retry=True, error_code="connector_failed")

    out = render_prometheus_text()
    assert 'yuantus_jobs_total{task_type="cad_convert",status="retry"} 1' in out
    assert 'yuantus_job_duration_ms_count{task_type="cad_convert",status="retry"} 1' in out


def test_fail_job_retry_does_not_emit_failure_status(session) -> None:
    _make_job(session, started_offset_ms=200)
    svc = JobService(session)
    svc.fail_job("job-1", "transient", retry=True)

    out = render_prometheus_text()
    assert 'status="retry"' in out
    assert 'yuantus_jobs_total{task_type="cad_convert",status="failure"}' not in out


def test_fail_job_retry_path_resets_started_at_after_metric(session) -> None:
    job = _make_job(session, started_offset_ms=200)
    svc = JobService(session)
    svc.fail_job("job-1", "transient", retry=True)

    session.refresh(job)
    assert job.started_at is None
    assert job.completed_at is None
    out = render_prometheus_text()
    assert 'yuantus_job_duration_ms_count{task_type="cad_convert",status="retry"} 1' in out


def test_complete_job_without_started_at_records_counter_only(session) -> None:
    job = ConversionJob(
        id="job-2",
        task_type="cad_convert",
        status=JobStatus.PROCESSING.value,
        payload={},
        started_at=None,
    )
    session.add(job)
    session.commit()
    JobService(session).complete_job("job-2")

    out = render_prometheus_text()
    assert 'yuantus_jobs_total{task_type="cad_convert",status="success"} 1' in out
    assert "yuantus_job_duration_ms" not in out


def test_empty_task_type_falls_back_to_unknown_label(session) -> None:
    job = ConversionJob(
        id="job-3",
        task_type="",
        status=JobStatus.PROCESSING.value,
        payload={},
        started_at=datetime.utcnow() - timedelta(milliseconds=100),
    )
    session.add(job)
    session.commit()
    JobService(session).complete_job("job-3")

    out = render_prometheus_text()
    assert 'yuantus_jobs_total{task_type="unknown",status="success"} 1' in out
