from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.job import ConversionJob as MetaConversionJob
from yuantus.meta_engine.web.file_router import (
    _PREVIEW_FORMATS,
    _meta_job_to_response,
)


def _make_file(file_id: str = "fc-1", *, is_cad: bool = True):
    return SimpleNamespace(
        id=file_id,
        filename="part.stp",
        file_type="stp",
        cad_format="STP",
        is_cad_file=lambda: is_cad,
    )


def _meta_job(
    job_id: str,
    *,
    task_type: str = "cad_geometry",
    status: str = "pending",
    file_id: str = "fc-1",
    target_format: str = "gltf",
):
    payload = {"file_id": file_id, "filename": "part.stp"}
    if task_type != "cad_preview":
        payload["target_format"] = target_format
    if status == "completed":
        payload["result"] = {"file_id": file_id}
    return SimpleNamespace(
        id=job_id,
        task_type=task_type,
        payload=payload,
        status=status,
        last_error=None,
        created_at=None,
        priority=10,
    )


def _client(*, file_container=None, meta_jobs=None, db_get=None):
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def default_db_get(model, identity):
        if db_get is not None:
            return db_get(model, identity)
        if model is FileContainer and file_container is not None and file_container.id == identity:
            return file_container
        return None

    def query_side_effect(model):
        query = MagicMock()
        if model is MetaConversionJob:
            query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = meta_jobs or []
            query.order_by.return_value.limit.return_value.all.return_value = meta_jobs or []
            return query
        return query

    mock_db.get.side_effect = default_db_get
    mock_db.query.side_effect = query_side_effect

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), mock_db


def test_conversion_queue_routes_registered():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/file/{file_id}/convert" in paths
    assert "/api/v1/file/conversion/{job_id}" in paths
    assert "/api/v1/file/conversions/pending" in paths
    assert "/api/v1/file/conversions/process" in paths


def test_meta_job_to_response_maps_preview():
    resp = _meta_job_to_response(
        _meta_job("meta-prev", task_type="cad_preview", status="pending")
    )
    assert resp.target_format == "png"
    assert resp.operation_type == "preview"


def test_preview_formats_classification_keeps_png_only():
    assert "png" in _PREVIEW_FORMATS
    assert "gltf" not in _PREVIEW_FORMATS


def test_request_conversion_queues_geometry_job_via_job_service():
    client, _ = _client(file_container=_make_file())
    queued = _meta_job("meta-1", task_type="cad_geometry", target_format="gltf")

    with patch("yuantus.meta_engine.web.file_router.JobService") as mock_service:
        mock_service.return_value.create_job.return_value = queued
        resp = client.post("/api/v1/file/fc-1/convert?target_format=gltf")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "meta-1"
    assert body["target_format"] == "gltf"
    call = mock_service.return_value.create_job.call_args
    assert call.args[0] == "cad_geometry"
    assert call.args[1]["file_id"] == "fc-1"
    assert call.args[1]["target_format"] == "gltf"


def test_request_conversion_queues_preview_job_for_png():
    client, _ = _client(file_container=_make_file())
    queued = _meta_job("meta-prev", task_type="cad_preview", target_format="png")

    with patch("yuantus.meta_engine.web.file_router.JobService") as mock_service:
        mock_service.return_value.create_job.return_value = queued
        resp = client.post("/api/v1/file/fc-1/convert?target_format=png")

    assert resp.status_code == 200
    assert resp.json()["operation_type"] == "preview"
    call = mock_service.return_value.create_job.call_args
    assert call.args[0] == "cad_preview"
    assert "target_format" not in call.args[1]


def test_get_conversion_status_prefers_meta_queue():
    meta = _meta_job("meta-status", task_type="cad_preview", status="completed")

    def db_get(model, identity):
        if model is MetaConversionJob and identity == "meta-status":
            return meta
        return None

    client, _ = _client(file_container=None, db_get=db_get)
    resp = client.get("/api/v1/file/conversion/meta-status")
    assert resp.status_code == 200
    assert resp.json()["id"] == "meta-status"


def test_get_conversion_status_404_for_unknown_job():
    client, _ = _client(file_container=None, db_get=lambda model, identity: None)
    resp = client.get("/api/v1/file/conversion/missing-job")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Conversion job not found"


def test_list_pending_conversions_reads_meta_only():
    client, _ = _client(
        file_container=_make_file(),
        meta_jobs=[_meta_job("meta-pending", task_type="cad_preview", status="pending")],
    )

    resp = client.get("/api/v1/file/conversions/pending?limit=2")
    assert resp.status_code == 200
    body = resp.json()
    assert [job["id"] for job in body] == ["meta-pending"]


def test_process_pending_conversions_delegates_to_filtered_worker():
    client, mock_db = _client(file_container=_make_file())
    job_ok = _meta_job("meta-ok", task_type="cad_geometry")
    job_fail = _meta_job("meta-fail", task_type="cad_preview")

    def execute_side_effect(job, job_service):
        if job.id == "meta-ok":
            job.status = "completed"
        else:
            job.status = "failed"

    fake_worker = MagicMock()
    fake_worker.worker_id = "file-router-conversions"
    fake_worker._execute_job.side_effect = execute_side_effect

    with patch("yuantus.meta_engine.web.file_router.JobService") as mock_service, patch(
        "yuantus.meta_engine.web.file_router._build_conversion_job_worker",
        return_value=fake_worker,
    ):
        svc = mock_service.return_value
        svc.requeue_stale_jobs.return_value = 0
        svc.poll_next_job.side_effect = [job_ok, job_fail, None]
        resp = client.post("/api/v1/file/conversions/process?batch_size=5")

    assert resp.status_code == 200
    assert resp.json() == {"processed": 2, "succeeded": 1, "failed": 1}
    poll_call = svc.poll_next_job.call_args
    assert poll_call.args[0] == "file-router-conversions"
    assert set(poll_call.kwargs["task_types"]) == {
        "cad_conversion",
        "cad_preview",
        "cad_geometry",
    }
    assert mock_db.refresh.call_count == 2


def test_process_cad_legacy_sets_deprecation_headers_and_queues_job():
    client, _ = _client(file_container=_make_file())
    queued = _meta_job("legacy-meta", task_type="cad_geometry", target_format="gltf")

    with patch("yuantus.meta_engine.web.file_router.JobService") as mock_service:
        mock_service.return_value.create_job.return_value = queued
        resp = client.post(
            "/api/v1/file/process_cad",
            json={"file_id": "fc-1", "target_format": "gltf"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "legacy-meta"
    assert body["status_url"] == "/api/v1/file/conversion/legacy-meta"
    assert body["viewable_url"] == "/api/v1/file/fc-1/geometry"
    assert resp.headers["Deprecation"] == "true"
    assert "Sunset" in resp.headers
    assert resp.headers["Link"] == '</api/v1/file/fc-1/convert>; rel="successor-version"'


def test_process_cad_legacy_rejects_non_cad_file_like_canonical_convert():
    client, _ = _client(file_container=_make_file(is_cad=False))
    resp = client.post(
        "/api/v1/file/process_cad",
        json={"file_id": "fc-1", "target_format": "gltf"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "File is not a CAD file"


def test_process_cad_legacy_missing_file_gives_clear_404():
    client, _ = _client(file_container=None)
    resp = client.post(
        "/api/v1/file/process_cad",
        json={"file_id": "missing", "target_format": "obj"},
    )
    assert resp.status_code == 404
    assert "Use POST /api/v1/file/{file_id}/convert" in resp.json()["detail"]
