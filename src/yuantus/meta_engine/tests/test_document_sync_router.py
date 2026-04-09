"""Tests for document_sync_router (C18 Document Multi-Site Sync Bootstrap)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.meta_engine.web.document_sync_router import document_sync_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app():
    app = FastAPI()
    app.include_router(document_sync_router, prefix="/api/v1")
    return app


def _client_with_mocks():
    from yuantus.api.dependencies.auth import get_current_user
    from yuantus.database import get_db

    mock_db = MagicMock()
    user = SimpleNamespace(id=200, roles=["engineer"], is_superuser=False)

    app = _make_app()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), mock_db


_FAKE_SITE = SimpleNamespace(
    id="site-1", name="HQ", description=None,
    base_url="https://hq.example.com", site_code="HQ",
    state="active", direction="push", is_primary=True,
)

_FAKE_JOB = SimpleNamespace(
    id="job-1", site_id="site-1", state="pending", direction="push",
    total_documents=0, synced_count=0, conflict_count=0,
    error_count=0, skipped_count=0,
)


# ---------------------------------------------------------------------------
# Site tests
# ---------------------------------------------------------------------------


def test_create_site():
    client, db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.create_site.return_value = _FAKE_SITE

        resp = client.post(
            "/api/v1/document-sync/sites",
            json={"name": "HQ", "site_code": "HQ"},
        )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["site_code"] == "HQ"
    assert db.commit.called


def test_list_sites():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.list_sites.return_value = [_FAKE_SITE]

        resp = client.get("/api/v1/document-sync/sites")

    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_get_site():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.get_site.return_value = _FAKE_SITE

        resp = client.get("/api/v1/document-sync/sites/site-1")

    assert resp.status_code == 200
    assert resp.json()["id"] == "site-1"


def test_get_site_not_found():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.get_site.return_value = None

        resp = client.get("/api/v1/document-sync/sites/nonexistent")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Job tests
# ---------------------------------------------------------------------------


def test_create_job():
    client, db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.create_job.return_value = _FAKE_JOB

        resp = client.post(
            "/api/v1/document-sync/jobs",
            json={"site_id": "site-1"},
        )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["site_id"] == "site-1"
    assert db.commit.called


def test_create_job_invalid_site_400():
    client, db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.create_job.side_effect = ValueError("Site not found")

        resp = client.post(
            "/api/v1/document-sync/jobs",
            json={"site_id": "bad"},
        )

    assert resp.status_code == 400
    assert db.rollback.called


def test_list_jobs():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.list_jobs.return_value = [_FAKE_JOB]

        resp = client.get("/api/v1/document-sync/jobs")

    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_get_job():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.get_job.return_value = _FAKE_JOB

        resp = client.get("/api/v1/document-sync/jobs/job-1")

    assert resp.status_code == 200
    assert resp.json()["id"] == "job-1"


def test_get_job_not_found():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.get_job.return_value = None

        resp = client.get("/api/v1/document-sync/jobs/nonexistent")

    assert resp.status_code == 404


def test_get_job_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_summary.return_value = {
            "job_id": "job-1",
            "site_id": "site-1",
            "state": "completed",
            "direction": "push",
            "total_records": 5,
            "by_outcome": {"synced": 3, "conflict": 1, "error": 1},
            "conflicts": [{"document_id": "d2", "source_checksum": "a", "target_checksum": "b", "detail": "mismatch"}],
            "errors": [{"document_id": "d3", "detail": "timeout"}],
        }

        resp = client.get("/api/v1/document-sync/jobs/job-1/summary")

    assert resp.status_code == 200
    assert resp.json()["total_records"] == 5
    assert resp.json()["by_outcome"]["synced"] == 3
    assert len(resp.json()["conflicts"]) == 1
    assert len(resp.json()["errors"]) == 1


def test_get_job_summary_not_found():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_summary.side_effect = ValueError("Job not found")

        resp = client.get("/api/v1/document-sync/jobs/bad/summary")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analytics / export endpoint tests (C21)
# ---------------------------------------------------------------------------


def test_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.overview.return_value = {
            "total_sites": 3, "sites_by_state": {"active": 2, "disabled": 1},
            "sites_by_direction": {"push": 2, "pull": 1},
            "total_jobs": 5, "jobs_by_state": {"completed": 3, "pending": 2},
            "total_conflicts": 4, "total_errors": 2,
        }
        resp = client.get("/api/v1/document-sync/overview")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 3
    assert resp.json()["total_jobs"] == 5
    assert resp.json()["total_conflicts"] == 4


def test_site_analytics():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_analytics.return_value = {
            "site_id": "site-1", "site_name": "HQ", "state": "active",
            "total_jobs": 2, "jobs_by_state": {"completed": 1, "pending": 1},
            "total_synced": 10, "total_conflicts": 2,
            "total_errors": 1, "total_skipped": 0,
        }
        resp = client.get("/api/v1/document-sync/sites/site-1/analytics")

    assert resp.status_code == 200
    assert resp.json()["total_synced"] == 10
    assert resp.json()["total_conflicts"] == 2


def test_site_analytics_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_analytics.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/x/analytics")

    assert resp.status_code == 404


def test_job_conflicts():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_conflicts.return_value = {
            "job_id": "job-1", "site_id": "site-1",
            "total_records": 5, "conflict_count": 2,
            "conflicts": [
                {"document_id": "d1", "source_checksum": "a", "target_checksum": "b", "detail": "mismatch"},
                {"document_id": "d2", "source_checksum": "c", "target_checksum": "d", "detail": "version"},
            ],
        }
        resp = client.get("/api/v1/document-sync/jobs/job-1/conflicts")

    assert resp.status_code == 200
    assert resp.json()["conflict_count"] == 2
    assert len(resp.json()["conflicts"]) == 2


def test_job_conflicts_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_conflicts.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/jobs/x/conflicts")

    assert resp.status_code == 404


def test_export_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_overview.return_value = {
            "overview": {"total_sites": 1, "total_jobs": 2,
                         "sites_by_state": {}, "sites_by_direction": {},
                         "jobs_by_state": {}, "total_conflicts": 0, "total_errors": 0},
        }
        resp = client.get("/api/v1/document-sync/export/overview")

    assert resp.status_code == 200
    assert "overview" in resp.json()


def test_export_conflicts():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_conflicts.return_value = {
            "total_conflicts": 1,
            "conflicts": [{"job_id": "j1", "site_id": "s1", "document_id": "d1",
                           "source_checksum": "a", "target_checksum": "b", "detail": "x"}],
        }
        resp = client.get("/api/v1/document-sync/export/conflicts")

    assert resp.status_code == 200
    assert resp.json()["total_conflicts"] == 1
    assert len(resp.json()["conflicts"]) == 1


# ---------------------------------------------------------------------------
# Reconciliation endpoint tests (C24)
# ---------------------------------------------------------------------------


def test_reconciliation_queue():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.reconciliation_queue.return_value = {
            "total_jobs_with_conflicts": 2,
            "jobs": [
                {"job_id": "j1", "site_id": "s1", "state": "completed",
                 "conflict_count": 3, "error_count": 1},
                {"job_id": "j2", "site_id": "s1", "state": "failed",
                 "conflict_count": 1, "error_count": 0},
            ],
        }
        resp = client.get("/api/v1/document-sync/reconciliation/queue")

    assert resp.status_code == 200
    assert resp.json()["total_jobs_with_conflicts"] == 2
    assert len(resp.json()["jobs"]) == 2


def test_conflict_resolution_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.conflict_resolution_summary.return_value = {
            "job_id": "j1", "site_id": "s1", "state": "completed",
            "total_records": 4, "synced": 1, "conflicts": 1,
            "errors": 1, "skipped": 1,
            "conflict_details": [
                {"record_id": "r2", "document_id": "d2",
                 "source_checksum": "aaa", "target_checksum": "bbb",
                 "detail": "version mismatch"},
            ],
            "error_details": [
                {"record_id": "r3", "document_id": "d3", "detail": "timeout"},
            ],
        }
        resp = client.get("/api/v1/document-sync/reconciliation/jobs/j1/summary")

    assert resp.status_code == 200
    assert resp.json()["total_records"] == 4
    assert resp.json()["conflicts"] == 1
    assert len(resp.json()["conflict_details"]) == 1
    assert len(resp.json()["error_details"]) == 1


def test_conflict_resolution_summary_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.conflict_resolution_summary.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/reconciliation/jobs/bad/summary")

    assert resp.status_code == 404


def test_site_reconciliation_status():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_reconciliation_status.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "total_jobs": 3, "jobs_with_conflicts": 1,
            "jobs_with_errors": 2, "total_unresolved_conflicts": 3,
            "total_unresolved_errors": 3,
        }
        resp = client.get("/api/v1/document-sync/reconciliation/sites/s1/status")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["jobs_with_conflicts"] == 1
    assert resp.json()["total_unresolved_conflicts"] == 3


def test_site_reconciliation_status_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_reconciliation_status.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/reconciliation/sites/bad/status")

    assert resp.status_code == 404


def test_export_reconciliation():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_reconciliation.return_value = {
            "reconciliation_queue": {
                "total_jobs_with_conflicts": 1,
                "jobs": [
                    {"job_id": "j1", "site_id": "s1", "state": "completed",
                     "conflict_count": 2, "error_count": 0},
                ],
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "total_jobs": 1, "jobs_with_conflicts": 1,
                 "jobs_with_errors": 0, "total_unresolved_conflicts": 2,
                 "total_unresolved_errors": 0},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/reconciliation")

    assert resp.status_code == 200
    assert "reconciliation_queue" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["reconciliation_queue"]["total_jobs_with_conflicts"] == 1
    assert len(resp.json()["sites"]) == 1


# ---------------------------------------------------------------------------
# Replay / audit endpoint tests (C27)
# ---------------------------------------------------------------------------


def test_replay_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.replay_overview.return_value = {
            "total_jobs": 4,
            "by_state": {"completed": 2, "failed": 1, "pending": 1},
            "retryable": 1,
            "replay_candidates": 1,
            "total_synced": 18,
            "total_documents": 25,
        }
        resp = client.get("/api/v1/document-sync/replay/overview")

    assert resp.status_code == 200
    assert resp.json()["total_jobs"] == 4
    assert resp.json()["retryable"] == 1
    assert resp.json()["replay_candidates"] == 1


def test_site_audit():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_audit.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "total_jobs": 3, "completed": 1, "failed": 1, "cancelled": 1,
            "total_synced": 10, "total_conflicts": 2, "total_errors": 3,
            "health_pct": 50.0,
        }
        resp = client.get("/api/v1/document-sync/sites/s1/audit")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["health_pct"] == 50.0
    assert resp.json()["completed"] == 1
    assert resp.json()["failed"] == 1


def test_site_audit_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_audit.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/bad/audit")

    assert resp.status_code == 404


def test_job_audit():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_audit.return_value = {
            "job_id": "j1", "site_id": "s1", "state": "completed",
            "direction": "push", "total_records": 3,
            "by_outcome": {"synced": 2, "conflict": 1},
            "checksum_mismatches": 1, "missing_checksums": 0,
            "is_retryable": False, "has_issues": True,
        }
        resp = client.get("/api/v1/document-sync/jobs/j1/audit")

    assert resp.status_code == 200
    assert resp.json()["job_id"] == "j1"
    assert resp.json()["checksum_mismatches"] == 1
    assert resp.json()["is_retryable"] is False
    assert resp.json()["has_issues"] is True


def test_job_audit_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_audit.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/jobs/bad/audit")

    assert resp.status_code == 404


def test_export_audit():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_audit.return_value = {
            "replay_overview": {
                "total_jobs": 2,
                "by_state": {"completed": 1, "failed": 1},
                "retryable": 1, "replay_candidates": 0,
                "total_synced": 10, "total_documents": 15,
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "total_jobs": 2, "completed": 1, "failed": 1,
                 "cancelled": 0, "total_synced": 10,
                 "total_conflicts": 0, "total_errors": 0,
                 "health_pct": 50.0},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/audit")

    assert resp.status_code == 200
    assert "replay_overview" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["replay_overview"]["total_jobs"] == 2
    assert len(resp.json()["sites"]) == 1


# ---------------------------------------------------------------------------
# Drift / Snapshots endpoint tests (C30)
# ---------------------------------------------------------------------------


def test_drift_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.drift_overview.return_value = {
            "total_sites": 2,
            "total_jobs": 3,
            "jobs_with_issues": 2,
            "drift_rate": 66.7,
            "sites_with_failed_jobs": 1,
            "total_synced_documents": 15,
            "total_conflicts": 2,
        }
        resp = client.get("/api/v1/document-sync/drift/overview")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["drift_rate"] == 66.7
    assert resp.json()["jobs_with_issues"] == 2
    assert resp.json()["total_synced_documents"] == 15


def test_site_snapshots():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_snapshots.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "direction": "push", "total_jobs": 3,
            "latest_job_state": "completed", "completed_jobs": 2,
            "total_synced": 15, "total_errors": 2, "total_conflicts": 1,
            "health_pct": 66.7,
        }
        resp = client.get("/api/v1/document-sync/sites/s1/snapshots")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["health_pct"] == 66.7
    assert resp.json()["completed_jobs"] == 2
    assert resp.json()["total_synced"] == 15


def test_site_snapshots_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_snapshots.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/bad/snapshots")

    assert resp.status_code == 404


def test_job_drift():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_drift.return_value = {
            "job_id": "j1", "state": "completed", "direction": "push",
            "total_documents": 10, "synced_count": 7,
            "conflict_count": 2, "error_count": 1, "skipped_count": 0,
            "drift_detected": True, "sync_completeness_pct": 70.0,
            "records_by_outcome": {"synced": 1, "conflict": 1, "error": 1},
        }
        resp = client.get("/api/v1/document-sync/jobs/j1/drift")

    assert resp.status_code == 200
    assert resp.json()["job_id"] == "j1"
    assert resp.json()["drift_detected"] is True
    assert resp.json()["sync_completeness_pct"] == 70.0
    assert resp.json()["records_by_outcome"]["synced"] == 1


def test_job_drift_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_drift.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/jobs/bad/drift")

    assert resp.status_code == 404


def test_export_drift():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_drift.return_value = {
            "drift_overview": {
                "total_sites": 1, "total_jobs": 1,
                "jobs_with_issues": 1, "drift_rate": 100.0,
                "sites_with_failed_jobs": 0,
                "total_synced_documents": 10, "total_conflicts": 1,
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "direction": "push", "total_jobs": 1,
                 "latest_job_state": "completed", "completed_jobs": 1,
                 "total_synced": 10, "total_errors": 0, "total_conflicts": 1,
                 "health_pct": 100.0},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/drift")

    assert resp.status_code == 200
    assert "drift_overview" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["drift_overview"]["total_sites"] == 1
    assert len(resp.json()["sites"]) == 1
    assert resp.json()["sites"][0]["site_id"] == "s1"


# ---------------------------------------------------------------------------
# Baseline / Lineage endpoint tests (C33)
# ---------------------------------------------------------------------------


def test_baseline_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.baseline_overview.return_value = {
            "total_sites": 2,
            "total_jobs": 4,
            "total_records": 15,
            "baseline_jobs": 2,
            "baseline_coverage_pct": 50.0,
            "sites_with_baseline": 2,
        }
        resp = client.get("/api/v1/document-sync/baseline/overview")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["total_jobs"] == 4
    assert resp.json()["total_records"] == 15
    assert resp.json()["baseline_jobs"] == 2
    assert resp.json()["baseline_coverage_pct"] == 50.0
    assert resp.json()["sites_with_baseline"] == 2


def test_site_lineage():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_lineage.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "direction": "push", "total_jobs": 3,
            "completed_jobs": 1, "failed_jobs": 1, "cancelled_jobs": 1,
            "total_synced": 10, "total_errors": 3, "lineage_depth": 3,
        }
        resp = client.get("/api/v1/document-sync/sites/s1/lineage")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["completed_jobs"] == 1
    assert resp.json()["failed_jobs"] == 1
    assert resp.json()["lineage_depth"] == 3
    assert resp.json()["total_synced"] == 10


def test_site_lineage_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_lineage.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/bad/lineage")

    assert resp.status_code == 404


def test_job_snapshot_lineage():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_snapshot_lineage.return_value = {
            "job_id": "j1", "state": "completed", "direction": "push",
            "total_documents": 10, "synced_count": 8,
            "conflict_count": 1, "error_count": 1, "skipped_count": 0,
            "is_baseline": True, "completeness_pct": 80.0,
            "records_by_outcome": {"synced": 1, "conflict": 1, "error": 1},
        }
        resp = client.get("/api/v1/document-sync/jobs/j1/snapshot-lineage")

    assert resp.status_code == 200
    assert resp.json()["job_id"] == "j1"
    assert resp.json()["is_baseline"] is True
    assert resp.json()["completeness_pct"] == 80.0
    assert resp.json()["records_by_outcome"]["synced"] == 1


def test_job_snapshot_lineage_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.job_snapshot_lineage.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/jobs/bad/snapshot-lineage")

    assert resp.status_code == 404


def test_export_lineage():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_lineage.return_value = {
            "baseline_overview": {
                "total_sites": 1, "total_jobs": 1,
                "total_records": 10, "baseline_jobs": 1,
                "baseline_coverage_pct": 100.0, "sites_with_baseline": 1,
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "direction": "push", "total_jobs": 1,
                 "completed_jobs": 1, "failed_jobs": 0, "cancelled_jobs": 0,
                 "total_synced": 10, "total_errors": 0, "lineage_depth": 1},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/lineage")

    assert resp.status_code == 200
    assert "baseline_overview" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["baseline_overview"]["total_sites"] == 1
    assert resp.json()["baseline_overview"]["baseline_jobs"] == 1
    assert len(resp.json()["sites"]) == 1
    assert resp.json()["sites"][0]["site_id"] == "s1"


# ---------------------------------------------------------------------------
# Checkpoints / Retention endpoint tests (C36)
# ---------------------------------------------------------------------------


def test_checkpoints_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.checkpoints_overview.return_value = {
            "total_sites": 2,
            "sites_by_state": {"active": 1, "disabled": 1},
            "total_jobs": 4,
            "completed_jobs": 2,
            "failed_jobs": 1,
            "completion_rate": 50.0,
            "total_synced": 15,
            "total_errors": 2,
            "retention_ready": False,
        }
        resp = client.get("/api/v1/document-sync/checkpoints/overview")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["total_jobs"] == 4
    assert resp.json()["completed_jobs"] == 2
    assert resp.json()["completion_rate"] == 50.0
    assert resp.json()["retention_ready"] is False


def test_retention_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.retention_summary.return_value = {
            "total_records": 20,
            "synced_records": 13,
            "conflict_records": 3,
            "error_records": 1,
            "skipped_records": 3,
            "conflict_retention_pct": 15.0,
            "error_retention_pct": 5.0,
            "clean_sync_pct": 65.0,
        }
        resp = client.get("/api/v1/document-sync/retention/summary")

    assert resp.status_code == 200
    assert resp.json()["total_records"] == 20
    assert resp.json()["synced_records"] == 13
    assert resp.json()["conflict_retention_pct"] == 15.0
    assert resp.json()["clean_sync_pct"] == 65.0


def test_site_checkpoints():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_checkpoints.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "total_checkpoints": 3, "completed_checkpoints": 2,
            "completion_rate": 66.7,
            "total_synced": 15, "total_errors": 3, "total_conflicts": 1,
            "checkpoints": [
                {"job_id": "j1", "state": "completed",
                 "synced_count": 10, "error_count": 0, "conflict_count": 1},
                {"job_id": "j2", "state": "failed",
                 "synced_count": 0, "error_count": 3, "conflict_count": 0},
                {"job_id": "j3", "state": "completed",
                 "synced_count": 5, "error_count": 0, "conflict_count": 0},
            ],
        }
        resp = client.get("/api/v1/document-sync/sites/s1/checkpoints")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["total_checkpoints"] == 3
    assert resp.json()["completed_checkpoints"] == 2
    assert resp.json()["completion_rate"] == 66.7
    assert len(resp.json()["checkpoints"]) == 3


def test_site_checkpoints_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_checkpoints.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/bad/checkpoints")

    assert resp.status_code == 404


def test_export_retention():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_retention.return_value = {
            "checkpoints_overview": {
                "total_sites": 1, "sites_by_state": {"active": 1},
                "total_jobs": 1, "completed_jobs": 1, "failed_jobs": 0,
                "completion_rate": 100.0, "total_synced": 10,
                "total_errors": 0, "retention_ready": True,
            },
            "retention_summary": {
                "total_records": 10, "synced_records": 10,
                "conflict_records": 0, "error_records": 0,
                "skipped_records": 0, "conflict_retention_pct": 0.0,
                "error_retention_pct": 0.0, "clean_sync_pct": 100.0,
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "total_checkpoints": 1, "completed_checkpoints": 1,
                 "completion_rate": 100.0, "total_synced": 10,
                 "total_errors": 0, "total_conflicts": 0,
                 "checkpoints": [
                     {"job_id": "j1", "state": "completed",
                      "synced_count": 10, "error_count": 0, "conflict_count": 0},
                 ]},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/retention")

    assert resp.status_code == 200
    assert "checkpoints_overview" in resp.json()
    assert "retention_summary" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["checkpoints_overview"]["total_sites"] == 1
    assert resp.json()["checkpoints_overview"]["retention_ready"] is True
    assert resp.json()["retention_summary"]["clean_sync_pct"] == 100.0
    assert len(resp.json()["sites"]) == 1
    assert resp.json()["sites"][0]["site_id"] == "s1"


def test_export_retention_empty():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_retention.return_value = {
            "checkpoints_overview": {
                "total_sites": 0, "sites_by_state": {},
                "total_jobs": 0, "completed_jobs": 0, "failed_jobs": 0,
                "completion_rate": None, "total_synced": 0,
                "total_errors": 0, "retention_ready": False,
            },
            "retention_summary": {
                "total_records": 0, "synced_records": 0,
                "conflict_records": 0, "error_records": 0,
                "skipped_records": 0, "conflict_retention_pct": None,
                "error_retention_pct": None, "clean_sync_pct": None,
            },
            "sites": [],
        }
        resp = client.get("/api/v1/document-sync/export/retention")

    assert resp.status_code == 200
    assert resp.json()["checkpoints_overview"]["total_sites"] == 0
    assert resp.json()["checkpoints_overview"]["retention_ready"] is False
    assert resp.json()["retention_summary"]["total_records"] == 0
    assert resp.json()["sites"] == []


# ---------------------------------------------------------------------------
# Freshness / Watermarks endpoint tests (C39)
# ---------------------------------------------------------------------------


def test_freshness_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.freshness_overview.return_value = {
            "total_sites": 2,
            "stale_site_count": 1,
            "avg_freshness_pct": 90.0,
            "freshest_site_id": "s2",
            "stalest_site_id": "s1",
        }
        resp = client.get("/api/v1/document-sync/freshness/overview")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["stale_site_count"] == 1
    assert resp.json()["avg_freshness_pct"] == 90.0
    assert resp.json()["freshest_site_id"] == "s2"
    assert resp.json()["stalest_site_id"] == "s1"


def test_watermarks_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.watermarks_summary.return_value = {
            "total_sites": 2,
            "exceeded_count": 1,
            "watermark_threshold": 50.0,
            "site_watermarks": [
                {"site_id": "s1", "freshness_pct": 30.0,
                 "high_watermark": 30.0, "low_watermark": 70.0, "exceeded": True},
                {"site_id": "s2", "freshness_pct": 90.0,
                 "high_watermark": 90.0, "low_watermark": 10.0, "exceeded": False},
            ],
        }
        resp = client.get("/api/v1/document-sync/watermarks/summary")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["exceeded_count"] == 1
    assert resp.json()["watermark_threshold"] == 50.0
    assert len(resp.json()["site_watermarks"]) == 2


def test_site_freshness():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_freshness.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "direction": "push", "total_records": 10,
            "synced_count": 7, "stale_doc_count": 3,
            "freshness_pct": 70.0,
        }
        resp = client.get("/api/v1/document-sync/sites/s1/freshness")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["freshness_pct"] == 70.0
    assert resp.json()["stale_doc_count"] == 3
    assert resp.json()["synced_count"] == 7


def test_site_freshness_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_freshness.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/bad/freshness")

    assert resp.status_code == 404


def test_export_watermarks():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_watermarks.return_value = {
            "freshness_overview": {
                "total_sites": 1, "stale_site_count": 0,
                "avg_freshness_pct": 100.0,
                "freshest_site_id": "s1", "stalest_site_id": "s1",
            },
            "watermarks_summary": {
                "total_sites": 1, "exceeded_count": 0,
                "watermark_threshold": 50.0,
                "site_watermarks": [
                    {"site_id": "s1", "freshness_pct": 100.0,
                     "high_watermark": 100.0, "low_watermark": 0.0,
                     "exceeded": False},
                ],
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "direction": "push", "total_records": 10,
                 "synced_count": 10, "stale_doc_count": 0,
                 "freshness_pct": 100.0},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/watermarks")

    assert resp.status_code == 200
    assert "freshness_overview" in resp.json()
    assert "watermarks_summary" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["freshness_overview"]["total_sites"] == 1
    assert resp.json()["watermarks_summary"]["exceeded_count"] == 0
    assert len(resp.json()["sites"]) == 1
    assert resp.json()["sites"][0]["site_id"] == "s1"


def test_export_watermarks_empty():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_watermarks.return_value = {
            "freshness_overview": {
                "total_sites": 0, "stale_site_count": 0,
                "avg_freshness_pct": None,
                "freshest_site_id": None, "stalest_site_id": None,
            },
            "watermarks_summary": {
                "total_sites": 0, "exceeded_count": 0,
                "watermark_threshold": 50.0,
                "site_watermarks": [],
            },
            "sites": [],
        }
        resp = client.get("/api/v1/document-sync/export/watermarks")

    assert resp.status_code == 200
    assert resp.json()["freshness_overview"]["total_sites"] == 0
    assert resp.json()["freshness_overview"]["avg_freshness_pct"] is None
    assert resp.json()["watermarks_summary"]["site_watermarks"] == []
    assert resp.json()["sites"] == []


# ---------------------------------------------------------------------------
# Lag / Backlog endpoint tests (C42)
# ---------------------------------------------------------------------------


def test_lag_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.lag_overview.return_value = {
            "total_sites": 2,
            "sites_with_pending": 1,
            "sites_with_failed": 1,
            "avg_lag": 1.0,
            "worst_lag_site_id": "s1",
        }
        resp = client.get("/api/v1/document-sync/lag/overview")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["sites_with_pending"] == 1
    assert resp.json()["sites_with_failed"] == 1
    assert resp.json()["avg_lag"] == 1.0
    assert resp.json()["worst_lag_site_id"] == "s1"


def test_backlog_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.backlog_summary.return_value = {
            "total_sites": 2,
            "total_pending": 5,
            "backlog_threshold": 3,
            "sites_above_threshold": 1,
            "backlog_distribution": [
                {"site_id": "s1", "pending_count": 4, "above_threshold": True},
                {"site_id": "s2", "pending_count": 1, "above_threshold": False},
            ],
        }
        resp = client.get("/api/v1/document-sync/backlog/summary")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["total_pending"] == 5
    assert resp.json()["sites_above_threshold"] == 1
    assert len(resp.json()["backlog_distribution"]) == 2


def test_site_backlog():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_backlog.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "total_jobs": 3, "pending_count": 1, "failed_count": 1,
            "synced_count": 1, "backlog_depth": 2,
        }
        resp = client.get("/api/v1/document-sync/sites/s1/backlog")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["pending_count"] == 1
    assert resp.json()["failed_count"] == 1
    assert resp.json()["backlog_depth"] == 2


def test_site_backlog_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_backlog.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/bad/backlog")

    assert resp.status_code == 404


def test_export_backlog():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_backlog.return_value = {
            "lag_overview": {
                "total_sites": 1, "sites_with_pending": 1,
                "sites_with_failed": 0, "avg_lag": 1.0,
                "worst_lag_site_id": "s1",
            },
            "backlog_summary": {
                "total_sites": 1, "total_pending": 1,
                "backlog_threshold": 3, "sites_above_threshold": 0,
                "backlog_distribution": [
                    {"site_id": "s1", "pending_count": 1, "above_threshold": False},
                ],
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "total_jobs": 2, "pending_count": 1, "failed_count": 0,
                 "synced_count": 1, "backlog_depth": 1},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/backlog")

    assert resp.status_code == 200
    assert "lag_overview" in resp.json()
    assert "backlog_summary" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["lag_overview"]["total_sites"] == 1
    assert resp.json()["backlog_summary"]["total_pending"] == 1
    assert len(resp.json()["sites"]) == 1
    assert resp.json()["sites"][0]["site_id"] == "s1"


def test_export_backlog_empty():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_backlog.return_value = {
            "lag_overview": {
                "total_sites": 0, "sites_with_pending": 0,
                "sites_with_failed": 0, "avg_lag": None,
                "worst_lag_site_id": None,
            },
            "backlog_summary": {
                "total_sites": 0, "total_pending": 0,
                "backlog_threshold": 3, "sites_above_threshold": 0,
                "backlog_distribution": [],
            },
            "sites": [],
        }
        resp = client.get("/api/v1/document-sync/export/backlog")

    assert resp.status_code == 200
    assert resp.json()["lag_overview"]["total_sites"] == 0
    assert resp.json()["lag_overview"]["avg_lag"] is None
    assert resp.json()["backlog_summary"]["backlog_distribution"] == []
    assert resp.json()["sites"] == []


# ---------------------------------------------------------------------------
# Skew / Gaps endpoint tests (C45)
# ---------------------------------------------------------------------------


def test_skew_overview():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.skew_overview.return_value = {
            "total_sites": 2,
            "sites_with_gaps": 1,
            "avg_gap_count": 1.0,
            "worst_gap_site_id": "s1",
        }
        resp = client.get("/api/v1/document-sync/skew/overview")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["sites_with_gaps"] == 1
    assert resp.json()["avg_gap_count"] == 1.0
    assert resp.json()["worst_gap_site_id"] == "s1"


def test_gaps_summary():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.gaps_summary.return_value = {
            "total_sites": 2,
            "total_gaps": 4,
            "gap_threshold": 2,
            "sites_above_threshold": 1,
            "severity_distribution": {
                "critical": 0, "warning": 1, "minor": 1, "clean": 0,
            },
        }
        resp = client.get("/api/v1/document-sync/gaps/summary")

    assert resp.status_code == 200
    assert resp.json()["total_sites"] == 2
    assert resp.json()["total_gaps"] == 4
    assert resp.json()["sites_above_threshold"] == 1
    assert resp.json()["severity_distribution"]["warning"] == 1


def test_site_gaps():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_gaps.return_value = {
            "site_id": "s1", "site_name": "HQ", "state": "active",
            "total_jobs": 3, "pending_count": 1, "failed_count": 1,
            "gap_count": 2, "severity": "minor",
        }
        resp = client.get("/api/v1/document-sync/sites/s1/gaps")

    assert resp.status_code == 200
    assert resp.json()["site_id"] == "s1"
    assert resp.json()["pending_count"] == 1
    assert resp.json()["failed_count"] == 1
    assert resp.json()["gap_count"] == 2
    assert resp.json()["severity"] == "minor"


def test_site_gaps_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.site_gaps.side_effect = ValueError("not found")
        resp = client.get("/api/v1/document-sync/sites/bad/gaps")

    assert resp.status_code == 404


def test_export_gaps():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_gaps.return_value = {
            "skew_overview": {
                "total_sites": 1, "sites_with_gaps": 1,
                "avg_gap_count": 1.0, "worst_gap_site_id": "s1",
            },
            "gaps_summary": {
                "total_sites": 1, "total_gaps": 1,
                "gap_threshold": 2, "sites_above_threshold": 0,
                "severity_distribution": {
                    "critical": 0, "warning": 0, "minor": 1, "clean": 0,
                },
            },
            "sites": [
                {"site_id": "s1", "site_name": "HQ", "state": "active",
                 "total_jobs": 2, "pending_count": 1, "failed_count": 0,
                 "gap_count": 1, "severity": "minor"},
            ],
        }
        resp = client.get("/api/v1/document-sync/export/gaps")

    assert resp.status_code == 200
    assert "skew_overview" in resp.json()
    assert "gaps_summary" in resp.json()
    assert "sites" in resp.json()
    assert resp.json()["skew_overview"]["total_sites"] == 1
    assert resp.json()["gaps_summary"]["total_gaps"] == 1
    assert len(resp.json()["sites"]) == 1
    assert resp.json()["sites"][0]["site_id"] == "s1"


def test_export_gaps_empty():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.document_sync_router.DocumentSyncService") as svc_cls:
        svc_cls.return_value.export_gaps.return_value = {
            "skew_overview": {
                "total_sites": 0, "sites_with_gaps": 0,
                "avg_gap_count": None, "worst_gap_site_id": None,
            },
            "gaps_summary": {
                "total_sites": 0, "total_gaps": 0,
                "gap_threshold": 2, "sites_above_threshold": 0,
                "severity_distribution": {
                    "critical": 0, "warning": 0, "minor": 0, "clean": 0,
                },
            },
            "sites": [],
        }
        resp = client.get("/api/v1/document-sync/export/gaps")

    assert resp.status_code == 200
    assert resp.json()["skew_overview"]["total_sites"] == 0
    assert resp.json()["skew_overview"]["avg_gap_count"] is None
    assert resp.json()["gaps_summary"]["severity_distribution"]["clean"] == 0
    assert resp.json()["sites"] == []
