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
