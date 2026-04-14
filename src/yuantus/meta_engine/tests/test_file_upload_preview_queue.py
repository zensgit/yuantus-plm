from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.security.auth.database import get_identity_db


def _client(*, duplicate=None):
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

    def query_side_effect(model):
        query = MagicMock()
        if model is FileContainer:
            query.filter.return_value.first.return_value = duplicate
            return query
        return query

    mock_db.query.side_effect = query_side_effect

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_identity_db] = override_get_identity_db
    return TestClient(app), mock_db


def test_cad_upload_queues_preview_job_and_returns_status_surface():
    client, _ = _client()
    queued = SimpleNamespace(id="job-prev-1")

    with patch("yuantus.meta_engine.web.file_router.FileService") as mock_fs, patch(
        "yuantus.meta_engine.web.file_router.JobService"
    ) as mock_jobs, patch(
        "yuantus.meta_engine.web.file_router.uuid.uuid4",
        return_value="11111111-1111-1111-1111-111111111111",
    ):
        mock_fs.return_value.upload_file.return_value = None
        mock_jobs.return_value.create_job.return_value = queued
        resp = client.post(
            "/api/v1/file/upload?generate_preview=true",
            files={"file": ("part.stp", io.BytesIO(b"step-data"), "model/step")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_cad"] is True
    assert body["conversion_job_ids"] == ["job-prev-1"]
    assert body["file_status_url"] == (
        "/api/v1/file/11111111-1111-1111-1111-111111111111/conversion_summary"
    )
    call = mock_jobs.return_value.create_job.call_args
    assert call.args[0] == "cad_preview"
    assert call.args[1]["file_id"] == "11111111-1111-1111-1111-111111111111"
    assert call.kwargs["priority"] == 50


def test_non_cad_upload_does_not_queue_preview_job():
    client, _ = _client()

    with patch("yuantus.meta_engine.web.file_router.FileService") as mock_fs, patch(
        "yuantus.meta_engine.web.file_router.JobService"
    ) as mock_jobs, patch(
        "yuantus.meta_engine.web.file_router.uuid.uuid4",
        return_value="22222222-2222-2222-2222-222222222222",
    ):
        mock_fs.return_value.upload_file.return_value = None
        resp = client.post(
            "/api/v1/file/upload?generate_preview=true",
            files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_cad"] is False
    assert body["conversion_job_ids"] == []
    assert body["file_status_url"] is None
    mock_jobs.return_value.create_job.assert_not_called()


def test_duplicate_cad_upload_returns_file_status_url_without_new_job():
    existing = SimpleNamespace(
        id="existing-cad",
        filename="existing.stp",
        file_size=123,
        mime_type="model/step",
        system_path="3d/ex/existing.stp",
        preview_path=None,
        cad_bom_path=None,
        cad_dedup_path=None,
        cad_document_schema_version=None,
        document_type="3d",
        author=None,
        source_system=None,
        source_version=None,
        document_version=None,
        is_cad_file=lambda: True,
    )
    client, _ = _client(duplicate=existing)

    with patch("yuantus.meta_engine.web.file_router.FileService") as mock_fs, patch(
        "yuantus.meta_engine.web.file_router.JobService"
    ) as mock_jobs:
        mock_fs.return_value.file_exists.return_value = True
        resp = client.post(
            "/api/v1/file/upload?generate_preview=true",
            files={"file": ("existing.stp", io.BytesIO(b"same"), "model/step")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "existing-cad"
    assert body["file_status_url"] == "/api/v1/file/existing-cad/conversion_summary"
    assert body["conversion_job_ids"] == []
    mock_jobs.return_value.create_job.assert_not_called()
