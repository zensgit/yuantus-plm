from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.job import ConversionJob as MetaConversionJob


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    """These tests override router dependencies; middleware auth is out of scope."""
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _make_file(file_id: str = "fc-1"):
    return SimpleNamespace(
        id=file_id,
        filename="part.stp",
        file_type="stp",
        mime_type="model/step",
        file_size=1024,
        checksum="abc123",
        document_type="3d",
        is_native_cad=True,
        cad_format="STP",
        system_path=f"/vault/{file_id}/part.stp",
        geometry_path=None,
        cad_manifest_path=None,
        preview_path=None,
        preview_data=None,
        cad_document_path=None,
        cad_metadata_path=None,
        cad_bom_path=None,
        cad_dedup_path=None,
        cad_document_schema_version=None,
        cad_review_state=None,
        cad_review_note=None,
        cad_review_by_id=None,
        cad_reviewed_at=None,
        conversion_status="pending",
        created_at=None,
    )


def _meta_job(job_id: str, status: str, task_type: str = "cad_geometry", file_id: str = "fc-1"):
    return SimpleNamespace(
        id=job_id,
        task_type=task_type,
        status=status,
        last_error=None,
        created_at=None,
        payload={
            "file_id": file_id,
            "target_format": "gltf",
            "result": {"file_id": file_id} if status == "completed" else {},
        },
    )


def _client(file_container=None, meta_jobs=None):
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def db_get(model, identity):
        if model is FileContainer and file_container is not None and file_container.id == identity:
            return file_container
        return None

    def query_side_effect(model):
        query = MagicMock()
        if model is MetaConversionJob:
            query.order_by.return_value.limit.return_value.all.return_value = meta_jobs or []
            return query
        return query

    mock_db.get.side_effect = db_get
    mock_db.query.side_effect = query_side_effect

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_file_conversion_summary_route_registered():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/file/{file_id}/conversion_summary" in paths


def test_file_conversion_summary_aggregates_meta_jobs():
    client = _client(
        file_container=_make_file(),
        meta_jobs=[
            _meta_job("meta-pending", "pending", task_type="cad_preview"),
            _meta_job("meta-completed", "completed", task_type="cad_geometry"),
        ],
    )

    from unittest.mock import patch

    with patch(
        "yuantus.meta_engine.web.file_conversion_router.CADConverterService.assess_viewer_readiness",
        return_value={"viewer_mode": "processing", "is_viewer_ready": False},
    ):
        resp = client.get("/api/v1/file/fc-1/conversion_summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["file_id"] == "fc-1"
    assert body["conversion_status"] == "pending"
    assert body["conversion_jobs_summary"] == {
        "pending": 1,
        "processing": 0,
        "completed": 1,
        "failed": 0,
        "total": 2,
    }
    assert {job["source"] for job in body["conversion_jobs"]} == {"meta"}
    assert body["viewer_readiness"]["viewer_mode"] == "processing"


def test_file_conversion_summary_404_for_missing_file():
    client = _client(file_container=None, meta_jobs=[])
    resp = client.get("/api/v1/file/missing/conversion_summary")
    assert resp.status_code == 404
