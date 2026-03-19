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
