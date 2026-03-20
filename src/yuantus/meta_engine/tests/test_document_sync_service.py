"""Tests for DocumentSyncService (C18 Document Multi-Site Sync Bootstrap)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.document_sync.models import (
    SiteState,
    SyncDirection,
    SyncJob,
    SyncJobState,
    SyncRecord,
    SyncRecordOutcome,
    SyncSite,
)
from yuantus.meta_engine.document_sync.service import DocumentSyncService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session():
    session = MagicMock()
    added = []
    session.add.side_effect = lambda obj: added.append(obj)
    session.flush.return_value = None
    session._added = added
    return session


def _make_site(site_id="site-1", name="HQ", state="active", direction="push"):
    site = MagicMock(spec=SyncSite)
    site.id = site_id
    site.name = name
    site.description = None
    site.base_url = "https://hq.example.com"
    site.site_code = "HQ"
    site.state = state
    site.direction = direction
    site.is_primary = True
    site.properties = None
    return site


def _make_job(job_id="job-1", site_id="site-1", state="pending", direction="push"):
    job = MagicMock(spec=SyncJob)
    job.id = job_id
    job.site_id = site_id
    job.state = state
    job.direction = direction
    job.total_documents = 0
    job.synced_count = 0
    job.conflict_count = 0
    job.error_count = 0
    job.skipped_count = 0
    job.properties = None
    return job


def _make_record(
    record_id="rec-1",
    job_id="job-1",
    document_id="doc-1",
    outcome="synced",
    source_checksum=None,
    target_checksum=None,
    conflict_detail=None,
    error_detail=None,
):
    rec = MagicMock(spec=SyncRecord)
    rec.id = record_id
    rec.job_id = job_id
    rec.document_id = document_id
    rec.outcome = outcome
    rec.source_checksum = source_checksum
    rec.target_checksum = target_checksum
    rec.conflict_detail = conflict_detail
    rec.error_detail = error_detail
    return rec


# ---------------------------------------------------------------------------
# TestSiteCRUD
# ---------------------------------------------------------------------------


class TestSiteCRUD:
    def test_create_site(self):
        session = _mock_session()
        service = DocumentSyncService(session)

        site = service.create_site(name="Factory A", site_code="FA")

        assert site.name == "Factory A"
        assert site.site_code == "FA"
        assert site.state == "active"
        assert session.add.called
        assert session.flush.called

    def test_get_site(self):
        session = _mock_session()
        fake_site = _make_site()
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        result = service.get_site("site-1")

        assert result is fake_site
        session.get.assert_called_once_with(SyncSite, "site-1")

    def test_list_sites_with_filters(self):
        session = _mock_session()
        fake_site = _make_site(state="active", direction="pull")
        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [fake_site]

        service = DocumentSyncService(session)
        result = service.list_sites(state="active", direction="pull")

        assert len(result) == 1

    def test_update_site(self):
        session = _mock_session()
        fake_site = _make_site()
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        result = service.update_site("site-1", name="Renamed Site")

        assert result is not None
        assert fake_site.name == "Renamed Site"

    def test_create_site_invalid_direction(self):
        session = _mock_session()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="Invalid direction"):
            service.create_site(name="Bad", site_code="X", direction="warp")


# ---------------------------------------------------------------------------
# TestSiteState
# ---------------------------------------------------------------------------


class TestSiteState:
    def test_active_to_disabled(self):
        session = _mock_session()
        fake_site = _make_site(state="active")
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        result = service.transition_site_state("site-1", "disabled")

        assert result.state == "disabled"

    def test_disabled_to_active(self):
        session = _mock_session()
        fake_site = _make_site(state="disabled")
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        result = service.transition_site_state("site-1", "active")

        assert result.state == "active"

    def test_archived_terminal(self):
        session = _mock_session()
        fake_site = _make_site(state="archived")
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.transition_site_state("site-1", "active")

    def test_invalid_transition(self):
        session = _mock_session()
        fake_site = _make_site(state="active")
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.transition_site_state("site-1", "pending")


# ---------------------------------------------------------------------------
# TestJobCRUD
# ---------------------------------------------------------------------------


class TestJobCRUD:
    def test_create_job(self):
        session = _mock_session()
        fake_site = _make_site(state="active")
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        job = service.create_job(site_id="site-1")

        assert job.site_id == "site-1"
        assert job.state == "pending"
        assert job.direction == "push"
        assert session.add.called

    def test_create_job_site_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="not found"):
            service.create_job(site_id="nonexistent")

    def test_create_job_site_disabled(self):
        session = _mock_session()
        fake_site = _make_site(state="disabled")
        session.get.return_value = fake_site

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="Cannot create job"):
            service.create_job(site_id="site-1")

    def test_get_job(self):
        session = _mock_session()
        fake_job = _make_job()
        session.get.return_value = fake_job

        service = DocumentSyncService(session)
        result = service.get_job("job-1")

        assert result is fake_job

    def test_list_jobs_with_filters(self):
        session = _mock_session()
        fake_job = _make_job()
        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [fake_job]

        service = DocumentSyncService(session)
        result = service.list_jobs(site_id="site-1", state="pending")

        assert len(result) == 1


# ---------------------------------------------------------------------------
# TestJobState
# ---------------------------------------------------------------------------


class TestJobState:
    def test_pending_to_running(self):
        session = _mock_session()
        fake_job = _make_job(state="pending")
        session.get.return_value = fake_job

        service = DocumentSyncService(session)
        result = service.transition_job_state("job-1", "running")

        assert result.state == "running"

    def test_running_to_completed(self):
        session = _mock_session()
        fake_job = _make_job(state="running")
        session.get.return_value = fake_job

        service = DocumentSyncService(session)
        result = service.transition_job_state("job-1", "completed")

        assert result.state == "completed"

    def test_completed_terminal(self):
        session = _mock_session()
        fake_job = _make_job(state="completed")
        session.get.return_value = fake_job

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.transition_job_state("job-1", "running")


# ---------------------------------------------------------------------------
# TestSyncRecords
# ---------------------------------------------------------------------------


class TestSyncRecords:
    def test_add_record(self):
        session = _mock_session()
        fake_job = _make_job()
        session.get.return_value = fake_job

        service = DocumentSyncService(session)
        record = service.add_record(
            "job-1",
            document_id="doc-42",
            source_checksum="abc123",
            target_checksum="abc123",
            outcome="synced",
        )

        assert record.document_id == "doc-42"
        assert record.outcome == "synced"
        assert session.add.called

    def test_add_record_invalid_outcome(self):
        session = _mock_session()
        fake_job = _make_job()
        session.get.return_value = fake_job

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="Invalid outcome"):
            service.add_record("job-1", document_id="doc-1", outcome="magic")

    def test_list_records(self):
        session = _mock_session()
        fake_record = MagicMock(spec=SyncRecord)
        fake_record.job_id = "job-1"
        fake_record.document_id = "doc-1"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [fake_record]

        service = DocumentSyncService(session)
        result = service.list_records("job-1")

        assert len(result) == 1
        assert result[0].document_id == "doc-1"


# ---------------------------------------------------------------------------
# TestJobSummary
# ---------------------------------------------------------------------------


class TestJobSummary:
    def test_job_summary_with_conflicts_and_errors(self):
        session = _mock_session()
        fake_job = _make_job()
        session.get.return_value = fake_job

        r_synced = MagicMock(spec=SyncRecord)
        r_synced.outcome = "synced"
        r_synced.document_id = "d1"

        r_conflict = MagicMock(spec=SyncRecord)
        r_conflict.outcome = "conflict"
        r_conflict.document_id = "d2"
        r_conflict.source_checksum = "aaa"
        r_conflict.target_checksum = "bbb"
        r_conflict.conflict_detail = "version mismatch"

        r_error = MagicMock(spec=SyncRecord)
        r_error.outcome = "error"
        r_error.document_id = "d3"
        r_error.error_detail = "timeout"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [r_synced, r_conflict, r_error]

        service = DocumentSyncService(session)
        summary = service.job_summary("job-1")

        assert summary["job_id"] == "job-1"
        assert summary["total_records"] == 3
        assert summary["by_outcome"]["synced"] == 1
        assert summary["by_outcome"]["conflict"] == 1
        assert summary["by_outcome"]["error"] == 1
        assert len(summary["conflicts"]) == 1
        assert summary["conflicts"][0]["document_id"] == "d2"
        assert len(summary["errors"]) == 1
        assert summary["errors"][0]["detail"] == "timeout"

    def test_job_summary_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="not found"):
            service.job_summary("nonexistent")


# ---------------------------------------------------------------------------
# TestAnalytics (C21)
# ---------------------------------------------------------------------------


class TestAnalytics:
    def _session_with_models(self, sites=None, jobs=None):
        """Session whose query() returns sites or jobs depending on model."""
        session = _mock_session()
        _sites = sites or []
        _jobs = jobs or []

        def mock_query(model):
            q = MagicMock()
            if model is SyncSite:
                q.all.return_value = _sites
            elif model is SyncJob:
                q.all.return_value = _jobs
            else:
                q.all.return_value = []
            q.filter.return_value = q
            q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query
        return session

    def test_overview(self):
        sites = [
            _make_site(site_id="s1", state="active", direction="push"),
            _make_site(site_id="s2", state="disabled", direction="pull"),
        ]
        jobs = [
            _make_job(job_id="j1", state="completed"),
            _make_job(job_id="j2", state="failed"),
        ]
        jobs[0].conflict_count = 2
        jobs[0].error_count = 0
        jobs[1].conflict_count = 1
        jobs[1].error_count = 3

        session = self._session_with_models(sites=sites, jobs=jobs)
        service = DocumentSyncService(session)
        result = service.overview()

        assert result["total_sites"] == 2
        assert result["sites_by_state"]["active"] == 1
        assert result["sites_by_state"]["disabled"] == 1
        assert result["sites_by_direction"]["push"] == 1
        assert result["sites_by_direction"]["pull"] == 1
        assert result["total_jobs"] == 2
        assert result["total_conflicts"] == 3
        assert result["total_errors"] == 3

    def test_overview_empty(self):
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.overview()

        assert result["total_sites"] == 0
        assert result["total_jobs"] == 0
        assert result["total_conflicts"] == 0

    def test_site_analytics(self):
        session = _mock_session()
        fake_site = _make_site(state="active")
        session.get.return_value = fake_site

        j1 = _make_job(job_id="j1", state="completed")
        j1.synced_count = 10
        j1.conflict_count = 2
        j1.error_count = 1
        j1.skipped_count = 0

        j2 = _make_job(job_id="j2", state="pending")
        j2.synced_count = 0
        j2.conflict_count = 0
        j2.error_count = 0
        j2.skipped_count = 0

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [j1, j2]

        service = DocumentSyncService(session)
        result = service.site_analytics("site-1")

        assert result["site_id"] == "site-1"
        assert result["total_jobs"] == 2
        assert result["jobs_by_state"]["completed"] == 1
        assert result["jobs_by_state"]["pending"] == 1
        assert result["total_synced"] == 10
        assert result["total_conflicts"] == 2
        assert result["total_errors"] == 1

    def test_site_analytics_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="not found"):
            service.site_analytics("nonexistent")

    def test_job_conflicts(self):
        session = _mock_session()
        fake_job = _make_job()
        session.get.return_value = fake_job

        r_synced = MagicMock(spec=SyncRecord)
        r_synced.outcome = "synced"
        r_synced.document_id = "d1"

        r_conflict = MagicMock(spec=SyncRecord)
        r_conflict.outcome = "conflict"
        r_conflict.document_id = "d2"
        r_conflict.source_checksum = "aaa"
        r_conflict.target_checksum = "bbb"
        r_conflict.conflict_detail = "version mismatch"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [r_synced, r_conflict]

        service = DocumentSyncService(session)
        result = service.job_conflicts("job-1")

        assert result["job_id"] == "job-1"
        assert result["total_records"] == 2
        assert result["conflict_count"] == 1
        assert result["conflicts"][0]["document_id"] == "d2"

    def test_job_conflicts_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = DocumentSyncService(session)
        with pytest.raises(ValueError, match="not found"):
            service.job_conflicts("nonexistent")

    def test_export_overview(self):
        session = self._session_with_models(
            sites=[_make_site()], jobs=[_make_job()]
        )
        service = DocumentSyncService(session)
        result = service.export_overview()

        assert "overview" in result
        assert result["overview"]["total_sites"] == 1
        assert result["overview"]["total_jobs"] == 1

    def test_export_conflicts(self):
        session = _mock_session()

        j1 = _make_job(job_id="j1")

        r_conflict = MagicMock(spec=SyncRecord)
        r_conflict.outcome = "conflict"
        r_conflict.document_id = "d2"
        r_conflict.source_checksum = "xxx"
        r_conflict.target_checksum = "yyy"
        r_conflict.conflict_detail = "checksum mismatch"

        r_ok = MagicMock(spec=SyncRecord)
        r_ok.outcome = "synced"

        def mock_query(model):
            q = MagicMock()
            if model is SyncJob:
                q.all.return_value = [j1]
            elif model is SyncRecord:
                q.all.return_value = [r_conflict, r_ok]
            else:
                q.all.return_value = []
            q.filter.return_value = q
            q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        service = DocumentSyncService(session)
        result = service.export_conflicts()

        assert result["total_conflicts"] == 1
        assert result["conflicts"][0]["job_id"] == "j1"
        assert result["conflicts"][0]["document_id"] == "d2"

    def test_export_conflicts_empty(self):
        session = _mock_session()

        def mock_query(model):
            q = MagicMock()
            q.all.return_value = []
            q.filter.return_value = q
            q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        service = DocumentSyncService(session)
        result = service.export_conflicts()

        assert result["total_conflicts"] == 0
        assert result["conflicts"] == []


# ---------------------------------------------------------------------------
# TestReconciliation (C24)
# ---------------------------------------------------------------------------


class TestReconciliation:
    def _session_with_models(self, sites=None, jobs=None, records=None):
        """Session whose query() returns sites, jobs, or records depending on model."""
        session = _mock_session()
        _sites = sites or []
        _jobs = jobs or []
        _records = records or []

        def _get_side_effect(model, pk):
            if model is SyncSite:
                return next((s for s in _sites if s.id == pk), None)
            if model is SyncJob:
                return next((j for j in _jobs if j.id == pk), None)
            return None

        session.get.side_effect = _get_side_effect

        def mock_query(model):
            q = MagicMock()
            if model is SyncSite:
                q.all.return_value = _sites
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is SyncJob:
                # Support both .all() and .filter().all() patterns
                q.all.return_value = _jobs

                def filter_side_effect(*args, **kwargs):
                    fq = MagicMock()
                    # Try to match by site_id filter
                    filtered = _jobs
                    fq.all.return_value = filtered
                    fq.filter.return_value = fq
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = filter_side_effect
                q.order_by.return_value = q
            elif model is SyncRecord:
                q.all.return_value = _records
                q.filter.return_value = q
                q.order_by.return_value = q
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query
        return session

    def test_reconciliation_queue(self):
        """Jobs with conflicts in completed/failed state appear in queue."""
        j1 = _make_job(job_id="j1", state="completed")
        j1.conflict_count = 3
        j1.error_count = 1

        j2 = _make_job(job_id="j2", state="failed")
        j2.conflict_count = 1
        j2.error_count = 0

        j3 = _make_job(job_id="j3", state="pending")
        j3.conflict_count = 5
        j3.error_count = 0

        session = self._session_with_models(jobs=[j1, j2, j3])
        service = DocumentSyncService(session)
        result = service.reconciliation_queue()

        assert result["total_jobs_with_conflicts"] == 2
        job_ids = [j["job_id"] for j in result["jobs"]]
        assert "j1" in job_ids
        assert "j2" in job_ids
        assert "j3" not in job_ids

    def test_reconciliation_queue_empty(self):
        """No jobs at all yields empty queue."""
        session = self._session_with_models(jobs=[])
        service = DocumentSyncService(session)
        result = service.reconciliation_queue()

        assert result["total_jobs_with_conflicts"] == 0
        assert result["jobs"] == []

    def test_reconciliation_queue_no_conflicts(self):
        """Jobs exist but none have conflicts."""
        j1 = _make_job(job_id="j1", state="completed")
        j1.conflict_count = 0
        j1.error_count = 0

        j2 = _make_job(job_id="j2", state="failed")
        j2.conflict_count = 0
        j2.error_count = 2

        session = self._session_with_models(jobs=[j1, j2])
        service = DocumentSyncService(session)
        result = service.reconciliation_queue()

        assert result["total_jobs_with_conflicts"] == 0
        assert result["jobs"] == []

    def test_conflict_resolution_summary(self):
        """Detailed breakdown includes record-level conflict and error details."""
        job = _make_job(job_id="j1", site_id="s1", state="completed")

        r_synced = _make_record(
            record_id="r1", document_id="d1", outcome="synced"
        )
        r_conflict = _make_record(
            record_id="r2",
            document_id="d2",
            outcome="conflict",
            source_checksum="aaa",
            target_checksum="bbb",
            conflict_detail="version mismatch",
        )
        r_error = _make_record(
            record_id="r3",
            document_id="d3",
            outcome="error",
            error_detail="timeout",
        )
        r_skipped = _make_record(
            record_id="r4", document_id="d4", outcome="skipped"
        )

        session = self._session_with_models(
            jobs=[job], records=[r_synced, r_conflict, r_error, r_skipped]
        )
        service = DocumentSyncService(session)
        result = service.conflict_resolution_summary("j1")

        assert result["job_id"] == "j1"
        assert result["site_id"] == "s1"
        assert result["state"] == "completed"
        assert result["total_records"] == 4
        assert result["synced"] == 1
        assert result["conflicts"] == 1
        assert result["errors"] == 1
        assert result["skipped"] == 1

        assert len(result["conflict_details"]) == 1
        assert result["conflict_details"][0]["record_id"] == "r2"
        assert result["conflict_details"][0]["document_id"] == "d2"
        assert result["conflict_details"][0]["source_checksum"] == "aaa"
        assert result["conflict_details"][0]["target_checksum"] == "bbb"
        assert result["conflict_details"][0]["detail"] == "version mismatch"

        assert len(result["error_details"]) == 1
        assert result["error_details"][0]["record_id"] == "r3"
        assert result["error_details"][0]["detail"] == "timeout"

    def test_conflict_resolution_summary_not_found(self):
        """Raises ValueError when job does not exist."""
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.conflict_resolution_summary("nonexistent")

    def test_conflict_resolution_summary_no_conflicts(self):
        """Summary works correctly when job has no conflict records."""
        job = _make_job(job_id="j1", site_id="s1", state="completed")

        r_synced = _make_record(
            record_id="r1", document_id="d1", outcome="synced"
        )
        r_synced2 = _make_record(
            record_id="r2", document_id="d2", outcome="synced"
        )

        session = self._session_with_models(
            jobs=[job], records=[r_synced, r_synced2]
        )
        service = DocumentSyncService(session)
        result = service.conflict_resolution_summary("j1")

        assert result["total_records"] == 2
        assert result["synced"] == 2
        assert result["conflicts"] == 0
        assert result["errors"] == 0
        assert result["skipped"] == 0
        assert result["conflict_details"] == []
        assert result["error_details"] == []

    def test_site_reconciliation_status(self):
        """Per-site status aggregates conflict/error counts across jobs."""
        site = _make_site(site_id="s1", name="HQ", state="active")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.conflict_count = 3
        j1.error_count = 1

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.conflict_count = 0
        j2.error_count = 2

        j3 = _make_job(job_id="j3", site_id="s1", state="pending")
        j3.conflict_count = 0
        j3.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1, j2, j3])
        service = DocumentSyncService(session)
        result = service.site_reconciliation_status("s1")

        assert result["site_id"] == "s1"
        assert result["site_name"] == "HQ"
        assert result["state"] == "active"
        assert result["total_jobs"] == 3
        assert result["jobs_with_conflicts"] == 1
        assert result["jobs_with_errors"] == 2
        assert result["total_unresolved_conflicts"] == 3
        assert result["total_unresolved_errors"] == 3

    def test_site_reconciliation_status_not_found(self):
        """Raises ValueError when site does not exist."""
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.site_reconciliation_status("nonexistent")

    def test_export_reconciliation(self):
        """Export payload contains queue and per-site breakdown."""
        site = _make_site(site_id="s1", name="HQ", state="active")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.conflict_count = 2
        j1.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1])
        service = DocumentSyncService(session)
        result = service.export_reconciliation()

        assert "reconciliation_queue" in result
        assert "sites" in result
        assert result["reconciliation_queue"]["total_jobs_with_conflicts"] == 1
        assert len(result["sites"]) == 1
        assert result["sites"][0]["site_id"] == "s1"
        assert result["sites"][0]["jobs_with_conflicts"] == 1


# ---------------------------------------------------------------------------
# TestReplayAudit (C27)
# ---------------------------------------------------------------------------


class TestReplayAudit:
    def _session_with_models(self, sites=None, jobs=None, records=None):
        """Session with model-aware query routing and session.get support."""
        session = _mock_session()
        _sites = sites or []
        _jobs = jobs or []
        _records = records or []

        def _get_side_effect(model, pk):
            if model is SyncSite:
                return next((s for s in _sites if s.id == pk), None)
            if model is SyncJob:
                return next((j for j in _jobs if j.id == pk), None)
            return None

        session.get.side_effect = _get_side_effect

        def mock_query(model):
            q = MagicMock()
            if model is SyncSite:
                q.all.return_value = _sites
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is SyncJob:
                q.all.return_value = _jobs

                def filter_side_effect(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = _jobs
                    fq.filter.return_value = fq
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = filter_side_effect
                q.order_by.return_value = q
            elif model is SyncRecord:
                q.all.return_value = _records
                q.filter.return_value = q
                q.order_by.return_value = q
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query
        return session

    def test_replay_overview(self):
        j1 = _make_job(job_id="j1", state="completed")
        j1.synced_count = 10
        j1.total_documents = 12
        j1.conflict_count = 1
        j1.error_count = 1

        j2 = _make_job(job_id="j2", state="failed")
        j2.synced_count = 0
        j2.total_documents = 5
        j2.conflict_count = 0
        j2.error_count = 0

        j3 = _make_job(job_id="j3", state="completed")
        j3.synced_count = 8
        j3.total_documents = 8
        j3.conflict_count = 0
        j3.error_count = 0

        j4 = _make_job(job_id="j4", state="pending")
        j4.synced_count = 0
        j4.total_documents = 0
        j4.conflict_count = 0
        j4.error_count = 0

        session = self._session_with_models(jobs=[j1, j2, j3, j4])
        service = DocumentSyncService(session)
        result = service.replay_overview()

        assert result["total_jobs"] == 4
        assert result["by_state"]["completed"] == 2
        assert result["by_state"]["failed"] == 1
        assert result["by_state"]["pending"] == 1
        assert result["retryable"] == 1  # j2 failed
        assert result["replay_candidates"] == 1  # j1 completed with issues
        assert result["total_synced"] == 18
        assert result["total_documents"] == 25

    def test_replay_overview_empty(self):
        session = self._session_with_models(jobs=[])
        service = DocumentSyncService(session)
        result = service.replay_overview()

        assert result["total_jobs"] == 0
        assert result["retryable"] == 0
        assert result["replay_candidates"] == 0

    def test_site_audit(self):
        site = _make_site(site_id="s1", name="HQ", state="active")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.conflict_count = 2
        j1.error_count = 0

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.synced_count = 0
        j2.conflict_count = 0
        j2.error_count = 3

        j3 = _make_job(job_id="j3", site_id="s1", state="cancelled")
        j3.synced_count = 0
        j3.conflict_count = 0
        j3.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1, j2, j3])
        service = DocumentSyncService(session)
        result = service.site_audit("s1")

        assert result["site_id"] == "s1"
        assert result["site_name"] == "HQ"
        assert result["total_jobs"] == 3
        assert result["completed"] == 1
        assert result["failed"] == 1
        assert result["cancelled"] == 1
        assert result["total_synced"] == 10
        assert result["total_conflicts"] == 2
        assert result["total_errors"] == 3
        # health: 1 completed / 2 finished = 50%
        assert result["health_pct"] == 50.0

    def test_site_audit_all_completed(self):
        site = _make_site(site_id="s1", name="HQ", state="active")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.conflict_count = 0
        j1.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1])
        service = DocumentSyncService(session)
        result = service.site_audit("s1")

        assert result["health_pct"] == 100.0

    def test_site_audit_no_finished_jobs(self):
        site = _make_site(site_id="s1", name="HQ", state="active")

        j1 = _make_job(job_id="j1", site_id="s1", state="pending")
        j1.synced_count = 0
        j1.conflict_count = 0
        j1.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1])
        service = DocumentSyncService(session)
        result = service.site_audit("s1")

        assert result["health_pct"] == 100.0  # no finished jobs = healthy

    def test_site_audit_not_found(self):
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.site_audit("nonexistent")

    def test_job_audit(self):
        job = _make_job(job_id="j1", site_id="s1", state="completed")
        job.conflict_count = 1
        job.error_count = 1

        r_synced = _make_record(
            record_id="r1", document_id="d1", outcome="synced",
            source_checksum="abc", target_checksum="abc",
        )
        r_conflict = _make_record(
            record_id="r2", document_id="d2", outcome="conflict",
            source_checksum="aaa", target_checksum="bbb",
        )
        r_no_checksum = _make_record(
            record_id="r3", document_id="d3", outcome="synced",
            source_checksum=None, target_checksum=None,
        )

        session = self._session_with_models(
            jobs=[job], records=[r_synced, r_conflict, r_no_checksum]
        )
        service = DocumentSyncService(session)
        result = service.job_audit("j1")

        assert result["job_id"] == "j1"
        assert result["total_records"] == 3
        assert result["by_outcome"]["synced"] == 2
        assert result["by_outcome"]["conflict"] == 1
        assert result["checksum_mismatches"] == 1  # r_conflict
        assert result["missing_checksums"] == 1  # r_no_checksum
        assert result["is_retryable"] is False  # completed, not failed
        assert result["has_issues"] is True  # conflict_count > 0

    def test_job_audit_failed_retryable(self):
        job = _make_job(job_id="j1", state="failed")
        job.conflict_count = 0
        job.error_count = 0

        session = self._session_with_models(jobs=[job], records=[])
        service = DocumentSyncService(session)
        result = service.job_audit("j1")

        assert result["is_retryable"] is True
        assert result["has_issues"] is False

    def test_job_audit_not_found(self):
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.job_audit("nonexistent")

    def test_export_audit(self):
        site = _make_site(site_id="s1", name="HQ", state="active")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 5
        j1.total_documents = 5
        j1.conflict_count = 0
        j1.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1])
        service = DocumentSyncService(session)
        result = service.export_audit()

        assert "replay_overview" in result
        assert "sites" in result
        assert result["replay_overview"]["total_jobs"] == 1
        assert len(result["sites"]) == 1
        assert result["sites"][0]["site_id"] == "s1"
        assert result["sites"][0]["health_pct"] == 100.0


# ---------------------------------------------------------------------------
# TestDriftSnapshots (C30)
# ---------------------------------------------------------------------------


class TestDriftSnapshots:
    def _session_with_models(self, sites=None, jobs=None, records=None):
        """Session with model-aware query routing and session.get support."""
        session = _mock_session()
        _sites = sites or []
        _jobs = jobs or []
        _records = records or []

        def _get_side_effect(model, pk):
            if model is SyncSite:
                return next((s for s in _sites if s.id == pk), None)
            if model is SyncJob:
                return next((j for j in _jobs if j.id == pk), None)
            return None

        session.get.side_effect = _get_side_effect

        def mock_query(model):
            q = MagicMock()
            if model is SyncSite:
                q.all.return_value = _sites
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is SyncJob:
                q.all.return_value = _jobs

                def filter_side_effect(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = _jobs
                    fq.filter.return_value = fq
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = filter_side_effect
                q.order_by.return_value = q
            elif model is SyncRecord:
                q.all.return_value = _records
                q.filter.return_value = q
                q.order_by.return_value = q
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query
        return session

    def test_drift_overview(self):
        """Sites with jobs having issues produce correct drift_rate."""
        sites = [
            _make_site(site_id="s1", state="active", direction="push"),
            _make_site(site_id="s2", state="active", direction="pull"),
        ]

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.conflict_count = 2
        j1.error_count = 0

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.synced_count = 0
        j2.conflict_count = 0
        j2.error_count = 3

        j3 = _make_job(job_id="j3", site_id="s2", state="completed")
        j3.synced_count = 5
        j3.conflict_count = 0
        j3.error_count = 0

        session = self._session_with_models(sites=sites, jobs=[j1, j2, j3])
        service = DocumentSyncService(session)
        result = service.drift_overview()

        assert result["total_sites"] == 2
        assert result["total_jobs"] == 3
        assert result["jobs_with_issues"] == 2  # j1 has conflicts, j2 has errors
        # drift_rate = 2/3 * 100 = 66.7
        assert result["drift_rate"] == 66.7
        assert result["sites_with_failed_jobs"] == 1  # s1 has j2 failed
        assert result["total_synced_documents"] == 15
        assert result["total_conflicts"] == 2

    def test_drift_overview_empty(self):
        """No sites/jobs yields None drift_rate and zero counts."""
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.drift_overview()

        assert result["total_sites"] == 0
        assert result["total_jobs"] == 0
        assert result["jobs_with_issues"] == 0
        assert result["drift_rate"] is None
        assert result["sites_with_failed_jobs"] == 0
        assert result["total_synced_documents"] == 0
        assert result["total_conflicts"] == 0

    def test_site_snapshots(self):
        """Site with multiple jobs produces correct health_pct."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.conflict_count = 1
        j1.error_count = 0

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.synced_count = 0
        j2.conflict_count = 0
        j2.error_count = 2

        j3 = _make_job(job_id="j3", site_id="s1", state="completed")
        j3.synced_count = 5
        j3.conflict_count = 0
        j3.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1, j2, j3])
        service = DocumentSyncService(session)
        result = service.site_snapshots("s1")

        assert result["site_id"] == "s1"
        assert result["site_name"] == "HQ"
        assert result["state"] == "active"
        assert result["direction"] == "push"
        assert result["total_jobs"] == 3
        assert result["completed_jobs"] == 2
        assert result["total_synced"] == 15
        assert result["total_errors"] == 2
        assert result["total_conflicts"] == 1
        # health_pct: 2 completed / 3 total = 66.7
        assert result["health_pct"] == 66.7
        # latest_job_state is last in the list
        assert result["latest_job_state"] == "completed"

    def test_site_snapshots_no_jobs(self):
        """Site exists but has no jobs; health_pct is None."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        session = self._session_with_models(sites=[site], jobs=[])
        service = DocumentSyncService(session)
        result = service.site_snapshots("s1")

        assert result["site_id"] == "s1"
        assert result["total_jobs"] == 0
        assert result["completed_jobs"] == 0
        assert result["health_pct"] is None
        assert result["latest_job_state"] is None

    def test_site_snapshots_not_found(self):
        """Raises ValueError when site does not exist."""
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.site_snapshots("nonexistent")

    def test_job_drift(self):
        """Job with errors/conflicts has drift_detected=True."""
        job = _make_job(job_id="j1", site_id="s1", state="completed", direction="push")
        job.total_documents = 10
        job.synced_count = 7
        job.conflict_count = 2
        job.error_count = 1
        job.skipped_count = 0

        r_synced = _make_record(record_id="r1", document_id="d1", outcome="synced")
        r_conflict = _make_record(record_id="r2", document_id="d2", outcome="conflict")
        r_error = _make_record(record_id="r3", document_id="d3", outcome="error")

        session = self._session_with_models(
            jobs=[job], records=[r_synced, r_conflict, r_error]
        )
        service = DocumentSyncService(session)
        result = service.job_drift("j1")

        assert result["job_id"] == "j1"
        assert result["state"] == "completed"
        assert result["direction"] == "push"
        assert result["total_documents"] == 10
        assert result["synced_count"] == 7
        assert result["conflict_count"] == 2
        assert result["error_count"] == 1
        assert result["skipped_count"] == 0
        assert result["drift_detected"] is True
        # sync_completeness_pct: 7/10 * 100 = 70.0
        assert result["sync_completeness_pct"] == 70.0
        assert result["records_by_outcome"]["synced"] == 1
        assert result["records_by_outcome"]["conflict"] == 1
        assert result["records_by_outcome"]["error"] == 1

    def test_job_drift_clean(self):
        """Job with no issues has drift_detected=False."""
        job = _make_job(job_id="j1", site_id="s1", state="completed", direction="push")
        job.total_documents = 5
        job.synced_count = 5
        job.conflict_count = 0
        job.error_count = 0
        job.skipped_count = 0

        r1 = _make_record(record_id="r1", document_id="d1", outcome="synced")
        r2 = _make_record(record_id="r2", document_id="d2", outcome="synced")

        session = self._session_with_models(jobs=[job], records=[r1, r2])
        service = DocumentSyncService(session)
        result = service.job_drift("j1")

        assert result["drift_detected"] is False
        assert result["sync_completeness_pct"] == 100.0
        assert result["records_by_outcome"]["synced"] == 2

    def test_job_drift_not_found(self):
        """Raises ValueError when job does not exist."""
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.job_drift("nonexistent")

    def test_export_drift(self):
        """Export combines drift_overview + per-site snapshots."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.conflict_count = 1
        j1.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1])
        service = DocumentSyncService(session)
        result = service.export_drift()

        assert "drift_overview" in result
        assert "sites" in result
        assert result["drift_overview"]["total_sites"] == 1
        assert result["drift_overview"]["total_jobs"] == 1
        assert result["drift_overview"]["jobs_with_issues"] == 1
        assert len(result["sites"]) == 1
        assert result["sites"][0]["site_id"] == "s1"
        assert result["sites"][0]["completed_jobs"] == 1

    def test_export_drift_empty(self):
        """Export with no data returns empty structures."""
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.export_drift()

        assert result["drift_overview"]["total_sites"] == 0
        assert result["drift_overview"]["total_jobs"] == 0
        assert result["drift_overview"]["drift_rate"] is None
        assert result["sites"] == []


# ---------------------------------------------------------------------------
# TestBaselineLineage (C33)
# ---------------------------------------------------------------------------


class TestBaselineLineage:
    def _session_with_models(self, sites=None, jobs=None, records=None):
        """Session with model-aware query routing and session.get support."""
        session = _mock_session()
        _sites = sites or []
        _jobs = jobs or []
        _records = records or []

        def _get_side_effect(model, pk):
            if model is SyncSite:
                return next((s for s in _sites if s.id == pk), None)
            if model is SyncJob:
                return next((j for j in _jobs if j.id == pk), None)
            return None

        session.get.side_effect = _get_side_effect

        def mock_query(model):
            q = MagicMock()
            if model is SyncSite:
                q.all.return_value = _sites
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is SyncJob:
                q.all.return_value = _jobs

                def filter_side_effect(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = _jobs
                    fq.filter.return_value = fq
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = filter_side_effect
                q.order_by.return_value = q
            elif model is SyncRecord:
                q.all.return_value = _records
                q.filter.return_value = q
                q.order_by.return_value = q
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query
        return session

    def test_baseline_overview(self):
        """Sites with completed jobs produce correct baseline_coverage_pct."""
        sites = [
            _make_site(site_id="s1", state="active", direction="push"),
            _make_site(site_id="s2", state="active", direction="pull"),
        ]

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.synced_count = 0

        j3 = _make_job(job_id="j3", site_id="s2", state="completed")
        j3.synced_count = 5

        j4 = _make_job(job_id="j4", site_id="s2", state="pending")
        j4.synced_count = 0

        session = self._session_with_models(sites=sites, jobs=[j1, j2, j3, j4])
        service = DocumentSyncService(session)
        result = service.baseline_overview()

        assert result["total_sites"] == 2
        assert result["total_jobs"] == 4
        assert result["total_records"] == 15  # 10 + 0 + 5 + 0
        assert result["baseline_jobs"] == 2  # j1, j3 completed
        # baseline_coverage_pct: 2/4 * 100 = 50.0
        assert result["baseline_coverage_pct"] == 50.0
        assert result["sites_with_baseline"] == 2  # s1 and s2 each have a completed job

    def test_baseline_overview_empty(self):
        """No sites/jobs yields None coverage and zero counts."""
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.baseline_overview()

        assert result["total_sites"] == 0
        assert result["total_jobs"] == 0
        assert result["total_records"] == 0
        assert result["baseline_jobs"] == 0
        assert result["baseline_coverage_pct"] is None
        assert result["sites_with_baseline"] == 0

    def test_site_lineage(self):
        """Site with multiple jobs in various states."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.error_count = 0

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.synced_count = 0
        j2.error_count = 3

        j3 = _make_job(job_id="j3", site_id="s1", state="cancelled")
        j3.synced_count = 0
        j3.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1, j2, j3])
        service = DocumentSyncService(session)
        result = service.site_lineage("s1")

        assert result["site_id"] == "s1"
        assert result["site_name"] == "HQ"
        assert result["state"] == "active"
        assert result["direction"] == "push"
        assert result["total_jobs"] == 3
        assert result["completed_jobs"] == 1
        assert result["failed_jobs"] == 1
        assert result["cancelled_jobs"] == 1
        assert result["total_synced"] == 10
        assert result["total_errors"] == 3
        assert result["lineage_depth"] == 3

    def test_site_lineage_no_jobs(self):
        """Site exists but has no jobs."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        session = self._session_with_models(sites=[site], jobs=[])
        service = DocumentSyncService(session)
        result = service.site_lineage("s1")

        assert result["site_id"] == "s1"
        assert result["total_jobs"] == 0
        assert result["completed_jobs"] == 0
        assert result["failed_jobs"] == 0
        assert result["cancelled_jobs"] == 0
        assert result["total_synced"] == 0
        assert result["total_errors"] == 0
        assert result["lineage_depth"] == 0

    def test_site_lineage_not_found(self):
        """Raises ValueError when site does not exist."""
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.site_lineage("nonexistent")

    def test_job_snapshot_lineage(self):
        """Completed job with records produces is_baseline=True."""
        job = _make_job(job_id="j1", site_id="s1", state="completed", direction="push")
        job.total_documents = 10
        job.synced_count = 8
        job.conflict_count = 1
        job.error_count = 1
        job.skipped_count = 0

        r_synced = _make_record(record_id="r1", document_id="d1", outcome="synced")
        r_conflict = _make_record(record_id="r2", document_id="d2", outcome="conflict")
        r_error = _make_record(record_id="r3", document_id="d3", outcome="error")

        session = self._session_with_models(
            jobs=[job], records=[r_synced, r_conflict, r_error]
        )
        service = DocumentSyncService(session)
        result = service.job_snapshot_lineage("j1")

        assert result["job_id"] == "j1"
        assert result["state"] == "completed"
        assert result["direction"] == "push"
        assert result["total_documents"] == 10
        assert result["synced_count"] == 8
        assert result["conflict_count"] == 1
        assert result["error_count"] == 1
        assert result["skipped_count"] == 0
        assert result["is_baseline"] is True
        # completeness_pct: 8/10 * 100 = 80.0
        assert result["completeness_pct"] == 80.0
        assert result["records_by_outcome"]["synced"] == 1
        assert result["records_by_outcome"]["conflict"] == 1
        assert result["records_by_outcome"]["error"] == 1

    def test_job_snapshot_lineage_pending(self):
        """Non-completed job has is_baseline=False."""
        job = _make_job(job_id="j1", site_id="s1", state="pending", direction="push")
        job.total_documents = 0
        job.synced_count = 0
        job.conflict_count = 0
        job.error_count = 0
        job.skipped_count = 0

        session = self._session_with_models(jobs=[job], records=[])
        service = DocumentSyncService(session)
        result = service.job_snapshot_lineage("j1")

        assert result["is_baseline"] is False
        assert result["completeness_pct"] is None
        assert result["records_by_outcome"] == {}

    def test_job_snapshot_lineage_not_found(self):
        """Raises ValueError when job does not exist."""
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.job_snapshot_lineage("nonexistent")

    def test_export_lineage(self):
        """Export combines baseline_overview + per-site lineages."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.error_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1])
        service = DocumentSyncService(session)
        result = service.export_lineage()

        assert "baseline_overview" in result
        assert "sites" in result
        assert result["baseline_overview"]["total_sites"] == 1
        assert result["baseline_overview"]["total_jobs"] == 1
        assert result["baseline_overview"]["baseline_jobs"] == 1
        assert len(result["sites"]) == 1
        assert result["sites"][0]["site_id"] == "s1"
        assert result["sites"][0]["completed_jobs"] == 1
        assert result["sites"][0]["lineage_depth"] == 1

    def test_export_lineage_empty(self):
        """Export with no data returns empty structures."""
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.export_lineage()

        assert result["baseline_overview"]["total_sites"] == 0
        assert result["baseline_overview"]["total_jobs"] == 0
        assert result["baseline_overview"]["baseline_coverage_pct"] is None
        assert result["sites"] == []


# ---------------------------------------------------------------------------
# TestCheckpointsRetention (C36)
# ---------------------------------------------------------------------------


class TestCheckpointsRetention:
    def _session_with_models(self, sites=None, jobs=None, records=None):
        """Session with model-aware query routing and session.get support."""
        session = _mock_session()
        _sites = sites or []
        _jobs = jobs or []
        _records = records or []

        def _get_side_effect(model, pk):
            if model is SyncSite:
                return next((s for s in _sites if s.id == pk), None)
            if model is SyncJob:
                return next((j for j in _jobs if j.id == pk), None)
            return None

        session.get.side_effect = _get_side_effect

        def mock_query(model):
            q = MagicMock()
            if model is SyncSite:
                q.all.return_value = _sites
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is SyncJob:
                q.all.return_value = _jobs

                def filter_side_effect(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = _jobs
                    fq.filter.return_value = fq
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = filter_side_effect
                q.order_by.return_value = q
            elif model is SyncRecord:
                q.all.return_value = _records
                q.filter.return_value = q
                q.order_by.return_value = q
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query
        return session

    def test_checkpoints_overview(self):
        """Sites with mixed job states produce correct completion rate and retention readiness."""
        sites = [
            _make_site(site_id="s1", state="active", direction="push"),
            _make_site(site_id="s2", state="disabled", direction="pull"),
        ]

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.error_count = 0

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.synced_count = 0
        j2.error_count = 2

        j3 = _make_job(job_id="j3", site_id="s2", state="completed")
        j3.synced_count = 5
        j3.error_count = 0

        j4 = _make_job(job_id="j4", site_id="s2", state="pending")
        j4.synced_count = 0
        j4.error_count = 0

        session = self._session_with_models(sites=sites, jobs=[j1, j2, j3, j4])
        service = DocumentSyncService(session)
        result = service.checkpoints_overview()

        assert result["total_sites"] == 2
        assert result["sites_by_state"] == {"active": 1, "disabled": 1}
        assert result["total_jobs"] == 4
        assert result["completed_jobs"] == 2
        assert result["failed_jobs"] == 1
        # completion_rate: 2/4 * 100 = 50.0
        assert result["completion_rate"] == 50.0
        assert result["total_synced"] == 15  # 10 + 0 + 5 + 0
        assert result["total_errors"] == 2
        # retention_ready is False because total_errors > 0
        assert result["retention_ready"] is False

    def test_checkpoints_overview_empty(self):
        """No sites/jobs yields None completion rate and not retention_ready."""
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.checkpoints_overview()

        assert result["total_sites"] == 0
        assert result["sites_by_state"] == {}
        assert result["total_jobs"] == 0
        assert result["completed_jobs"] == 0
        assert result["failed_jobs"] == 0
        assert result["completion_rate"] is None
        assert result["total_synced"] == 0
        assert result["total_errors"] == 0
        assert result["retention_ready"] is False

    def test_retention_summary(self):
        """Jobs with mixed outcomes produce correct retention percentages."""
        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 8
        j1.conflict_count = 1
        j1.error_count = 1
        j1.skipped_count = 0

        j2 = _make_job(job_id="j2", site_id="s1", state="completed")
        j2.synced_count = 5
        j2.conflict_count = 2
        j2.error_count = 0
        j2.skipped_count = 3

        session = self._session_with_models(jobs=[j1, j2])
        service = DocumentSyncService(session)
        result = service.retention_summary()

        # total_records: (8+1+1+0) + (5+2+0+3) = 10 + 10 = 20
        assert result["total_records"] == 20
        assert result["synced_records"] == 13  # 8 + 5
        assert result["conflict_records"] == 3  # 1 + 2
        assert result["error_records"] == 1
        assert result["skipped_records"] == 3
        # conflict_retention_pct: 3/20 * 100 = 15.0
        assert result["conflict_retention_pct"] == 15.0
        # error_retention_pct: 1/20 * 100 = 5.0
        assert result["error_retention_pct"] == 5.0
        # clean_sync_pct: 13/20 * 100 = 65.0
        assert result["clean_sync_pct"] == 65.0

    def test_retention_summary_no_records(self):
        """No jobs yields None percentages and zero counts."""
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.retention_summary()

        assert result["total_records"] == 0
        assert result["synced_records"] == 0
        assert result["conflict_records"] == 0
        assert result["error_records"] == 0
        assert result["skipped_records"] == 0
        assert result["conflict_retention_pct"] is None
        assert result["error_retention_pct"] is None
        assert result["clean_sync_pct"] is None

    def test_retention_summary_all_synced(self):
        """All records synced produces 100% clean_sync_pct."""
        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.conflict_count = 0
        j1.error_count = 0
        j1.skipped_count = 0

        session = self._session_with_models(jobs=[j1])
        service = DocumentSyncService(session)
        result = service.retention_summary()

        assert result["total_records"] == 10
        assert result["synced_records"] == 10
        assert result["clean_sync_pct"] == 100.0
        assert result["conflict_retention_pct"] == 0.0
        assert result["error_retention_pct"] == 0.0

    def test_site_checkpoints(self):
        """Site with multiple jobs produces checkpoint list and completion rate."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.error_count = 0
        j1.conflict_count = 1

        j2 = _make_job(job_id="j2", site_id="s1", state="failed")
        j2.synced_count = 0
        j2.error_count = 3
        j2.conflict_count = 0

        j3 = _make_job(job_id="j3", site_id="s1", state="completed")
        j3.synced_count = 5
        j3.error_count = 0
        j3.conflict_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1, j2, j3])
        service = DocumentSyncService(session)
        result = service.site_checkpoints("s1")

        assert result["site_id"] == "s1"
        assert result["site_name"] == "HQ"
        assert result["state"] == "active"
        assert result["total_checkpoints"] == 3
        assert result["completed_checkpoints"] == 2
        # completion_rate: 2/3 * 100 = 66.7
        assert result["completion_rate"] == 66.7
        assert result["total_synced"] == 15  # 10 + 0 + 5
        assert result["total_errors"] == 3
        assert result["total_conflicts"] == 1
        assert len(result["checkpoints"]) == 3
        assert result["checkpoints"][0]["job_id"] == "j1"
        assert result["checkpoints"][0]["state"] == "completed"
        assert result["checkpoints"][0]["synced_count"] == 10

    def test_site_checkpoints_no_jobs(self):
        """Site exists but has no jobs."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        session = self._session_with_models(sites=[site], jobs=[])
        service = DocumentSyncService(session)
        result = service.site_checkpoints("s1")

        assert result["site_id"] == "s1"
        assert result["total_checkpoints"] == 0
        assert result["completed_checkpoints"] == 0
        assert result["completion_rate"] is None
        assert result["total_synced"] == 0
        assert result["total_errors"] == 0
        assert result["total_conflicts"] == 0
        assert result["checkpoints"] == []

    def test_site_checkpoints_not_found(self):
        """Raises ValueError when site does not exist."""
        session = self._session_with_models()
        service = DocumentSyncService(session)

        with pytest.raises(ValueError, match="not found"):
            service.site_checkpoints("nonexistent")

    def test_export_retention(self):
        """Export combines checkpoints_overview + retention_summary + per-site details."""
        site = _make_site(site_id="s1", name="HQ", state="active", direction="push")

        j1 = _make_job(job_id="j1", site_id="s1", state="completed")
        j1.synced_count = 10
        j1.error_count = 0
        j1.conflict_count = 0
        j1.skipped_count = 0

        session = self._session_with_models(sites=[site], jobs=[j1])
        service = DocumentSyncService(session)
        result = service.export_retention()

        assert "checkpoints_overview" in result
        assert "retention_summary" in result
        assert "sites" in result
        assert result["checkpoints_overview"]["total_sites"] == 1
        assert result["checkpoints_overview"]["total_jobs"] == 1
        assert result["checkpoints_overview"]["completed_jobs"] == 1
        assert result["checkpoints_overview"]["retention_ready"] is True
        assert result["retention_summary"]["total_records"] == 10
        assert result["retention_summary"]["synced_records"] == 10
        assert len(result["sites"]) == 1
        assert result["sites"][0]["site_id"] == "s1"
        assert result["sites"][0]["total_checkpoints"] == 1

    def test_export_retention_empty(self):
        """Export with no data returns empty structures."""
        session = self._session_with_models()
        service = DocumentSyncService(session)
        result = service.export_retention()

        assert result["checkpoints_overview"]["total_sites"] == 0
        assert result["checkpoints_overview"]["total_jobs"] == 0
        assert result["checkpoints_overview"]["completion_rate"] is None
        assert result["checkpoints_overview"]["retention_ready"] is False
        assert result["retention_summary"]["total_records"] == 0
        assert result["retention_summary"]["clean_sync_pct"] is None
        assert result["sites"] == []
