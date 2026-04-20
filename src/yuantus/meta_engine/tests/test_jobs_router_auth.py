from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import (
    get_current_user_id,
    get_current_user_id_optional,
)
from yuantus.api.routers.jobs import router as jobs_router
from yuantus.database import get_db
from yuantus.security.auth.database import get_identity_db


def _make_client(authenticated: bool = False, user_id: int = 7):
    mock_db = MagicMock()
    mock_identity_db = MagicMock()

    app = FastAPI()
    app.include_router(jobs_router, prefix="/api/v1")

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def override_get_identity_db():
        try:
            yield mock_identity_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_identity_db] = override_get_identity_db
    if authenticated:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return TestClient(app), mock_db, mock_identity_db


def _make_job(job_id: str = "job-1", file_id: str = "file-1", created_by_id: int = 7):
    return SimpleNamespace(
        id=job_id,
        task_type="cad_conversion",
        payload={"file_id": file_id},
        status="queued",
        priority=10,
        worker_id=None,
        attempt_count=0,
        max_attempts=3,
        last_error=None,
        dedupe_key=None,
        created_at=None,
        scheduled_at=None,
        started_at=None,
        completed_at=None,
        created_by_id=created_by_id,
    )


def _make_file_container() -> SimpleNamespace:
    return SimpleNamespace(
        system_path="vault/private/file-1.step",
        cad_connector_id="cad-1",
        cad_format="STEP",
        document_type="cad",
        preview_path="/internal/previews/file-1.png",
        preview_data=None,
        geometry_path="/internal/geometry/file-1.glb",
        cad_manifest_path="/internal/cad/manifest.json",
        cad_document_path="/internal/cad/document.json",
        cad_metadata_path="/internal/cad/metadata.json",
        cad_bom_path="/internal/cad/bom.json",
    )


def test_get_current_user_id_optional_returns_none_without_authenticated_user() -> None:
    assert get_current_user_id_optional(None) is None
    assert get_current_user_id_optional(SimpleNamespace(id=17)) == 17


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("post", "/api/v1/jobs", {"json": {"task_type": "cad_conversion"}}),
        ("get", "/api/v1/jobs", {}),
        ("get", "/api/v1/jobs/job-1", {}),
    ],
)
def test_jobs_routes_require_authentication(method: str, path: str, kwargs: dict) -> None:
    client, _db, _identity_db = _make_client(authenticated=False)

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == 401


def test_create_job_uses_authenticated_user_id() -> None:
    client, _db, _identity_db = _make_client(authenticated=True, user_id=7)
    job = _make_job()

    with patch("yuantus.api.routers.jobs.get_request_context") as ctx_fn:
        with patch("yuantus.api.routers.jobs.JobService") as job_service_cls:
            ctx_fn.return_value = SimpleNamespace(tenant_id=None, org_id=None, user_id=7)
            job_service_cls.return_value.create_job.return_value = job

            response = client.post(
                "/api/v1/jobs",
                json={"task_type": "cad_conversion", "payload": {"file_id": "file-1"}},
            )

    assert response.status_code == 200
    assert response.json()["created_by_id"] == 7
    job_service_cls.return_value.create_job.assert_called_once_with(
        task_type="cad_conversion",
        payload={"file_id": "file-1"},
        user_id=7,
        priority=10,
        max_attempts=None,
        dedupe_key=None,
        dedupe=False,
    )


def test_list_jobs_returns_items_when_authenticated() -> None:
    client, mock_db, _identity_db = _make_client(authenticated=True, user_id=7)
    job = _make_job()
    query = MagicMock()
    mock_db.query.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = 1
    query.all.return_value = [job]

    response = client.get("/api/v1/jobs?limit=10")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "job-1"
    assert body["items"][0]["created_by_id"] == 7


def test_get_job_suppresses_internal_storage_paths_in_diagnostics() -> None:
    client, mock_db, _identity_db = _make_client(authenticated=True, user_id=7)
    job = _make_job()
    file_container = _make_file_container()
    mock_db.get.return_value = file_container

    with patch("yuantus.api.routers.jobs.JobService") as job_service_cls:
        with patch("yuantus.api.routers.jobs.FileService") as file_service_cls:
            job_service_cls.return_value.get_job.return_value = job
            file_service = file_service_cls.return_value
            file_service.file_exists.return_value = True

            response = client.get("/api/v1/jobs/job-1")

    assert response.status_code == 200
    diagnostics = response.json()["diagnostics"]
    assert diagnostics["file_id"] == "file-1"
    assert diagnostics["storage_exists"] is True
    assert isinstance(diagnostics["storage_head_latency_ms"], int)
    assert diagnostics["assets"] == {
        "preview": True,
        "geometry": True,
        "cad_manifest": True,
        "cad_document": True,
        "cad_metadata": True,
        "cad_bom": True,
    }
    assert "system_path" not in diagnostics
    assert "resolved_source_path" not in diagnostics
    for key in (
        "preview_path",
        "geometry_path",
        "cad_manifest_path",
        "cad_document_path",
        "cad_metadata_path",
        "cad_bom_path",
    ):
        assert key not in diagnostics
    file_service.file_exists.assert_called_once_with("vault/private/file-1.step")
