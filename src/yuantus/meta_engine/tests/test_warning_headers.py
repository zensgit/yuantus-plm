from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import Depends, FastAPI, Response
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.api.routers.jobs import router as jobs_router
from yuantus.api.warning_headers import (
    append_doc_sync_checkout_warning,
    append_quota_warning,
)
from yuantus.database import get_db
from yuantus.security.auth.database import get_identity_db


def test_append_quota_warning_appends_existing_value_and_ignores_blank_messages():
    response = Response()

    append_quota_warning(response, "files 10/10")
    append_quota_warning(response, "active_jobs 4/4")
    append_quota_warning(response, "   ")

    assert response.headers["X-Quota-Warning"] == "files 10/10; active_jobs 4/4"


def test_append_doc_sync_checkout_warning_appends_existing_value():
    response = Response()

    append_doc_sync_checkout_warning(response, "Checkout allowed despite doc-sync backlog")
    append_doc_sync_checkout_warning(response, "Checkout allowed despite doc-sync backlog")

    assert response.headers["X-Doc-Sync-Checkout-Warning"] == (
        "Checkout allowed despite doc-sync backlog; "
        "Checkout allowed despite doc-sync backlog"
    )


def _jobs_client_with_seed_warning() -> tuple[TestClient, MagicMock, MagicMock]:
    mock_db = MagicMock()
    mock_identity_db = MagicMock()

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

    def override_get_user_id():
        return 7

    def seed_warning(response: Response) -> None:
        response.headers["X-Quota-Warning"] = "tenant quota seeded"

    app = FastAPI()
    app.include_router(jobs_router, prefix="/api/v1", dependencies=[Depends(seed_warning)])
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_identity_db] = override_get_identity_db
    app.dependency_overrides[get_current_user_id_optional] = override_get_user_id
    return TestClient(app), mock_db, mock_identity_db


def test_create_job_appends_quota_warning_to_existing_header():
    client, mock_db, mock_identity_db = _jobs_client_with_seed_warning()

    job = SimpleNamespace(
        id="job-1",
        task_type="cad_conversion",
        payload={"file_id": "file-1"},
        status="queued",
        priority=10,
        worker_id=None,
        attempt_count=0,
        max_attempts=0,
        last_error=None,
        dedupe_key=None,
        created_at=None,
        scheduled_at=None,
        started_at=None,
        completed_at=None,
        created_by_id=7,
    )

    with patch("yuantus.api.routers.jobs.get_request_context") as ctx_fn:
        with patch("yuantus.api.routers.jobs.QuotaService") as quota_cls:
            with patch("yuantus.api.routers.jobs.JobService") as job_service_cls:
                ctx_fn.return_value = SimpleNamespace(tenant_id="tenant-1", org_id=None, user_id=7)
                quota_service = quota_cls.return_value
                quota_service.mode = "soft"
                quota_service.evaluate.return_value = [
                    SimpleNamespace(resource="active_jobs", used=0, requested=1, limit=1)
                ]
                quota_cls.build_warning.return_value = "active_jobs 1/1"
                job_service_cls.return_value.create_job.return_value = job

                resp = client.post(
                    "/api/v1/jobs",
                    json={
                        "task_type": "cad_conversion",
                        "payload": {"file_id": "file-1"},
                    },
                )

    assert resp.status_code == 200
    assert resp.headers["X-Quota-Warning"] == "tenant quota seeded; active_jobs 1/1"
    assert resp.json()["id"] == "job-1"
    job_service_cls.return_value.create_job.assert_called_once_with(
        task_type="cad_conversion",
        payload={"file_id": "file-1"},
        user_id=7,
        priority=10,
        max_attempts=None,
        dedupe_key=None,
        dedupe=False,
    )
    quota_service.evaluate.assert_called_once_with("tenant-1", deltas={"active_jobs": 1})
    mock_db  # keep fixtures referenced for readability
    mock_identity_db
