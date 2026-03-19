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
