from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.models.job import JobStatus


def test_get_pending_jobs_reads_meta_queue_only():
    session = MagicMock()
    service = CADConverterService(session)
    query = session.query.return_value
    filter1 = query.filter.return_value
    filter2 = filter1.filter.return_value
    filter2.order_by.return_value.limit.return_value.all.return_value = ["job-1"]

    jobs = service.get_pending_jobs(batch_size=5)

    assert jobs == ["job-1"]
    session.query.assert_called_once()


def test_process_batch_delegates_to_canonical_worker():
    session = MagicMock()
    service = CADConverterService(session)
    job_ok = SimpleNamespace(id="job-ok", status=JobStatus.PENDING.value)
    job_fail = SimpleNamespace(id="job-fail", status=JobStatus.PENDING.value)
    fake_worker = MagicMock()
    fake_worker.worker_id = "cad-converter-service"

    def execute_side_effect(job, job_service):
        if job.id == "job-ok":
            job.status = JobStatus.COMPLETED.value
        else:
            job.status = JobStatus.FAILED.value

    fake_worker._execute_job.side_effect = execute_side_effect

    with patch(
        "yuantus.meta_engine.services.cad_converter_service.JobService"
    ) as mock_jobs, patch(
        "yuantus.meta_engine.services.cad_converter_service._build_canonical_conversion_worker",
        return_value=fake_worker,
    ):
        svc = mock_jobs.return_value
        svc.poll_next_job.side_effect = [job_ok, job_fail, None]
        result = service.process_batch(batch_size=5)

    assert result == {"processed": 2, "succeeded": 1, "failed": 1}
    svc.requeue_stale_jobs.assert_called_once()
    assert session.refresh.call_count == 2
