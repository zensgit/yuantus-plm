from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.web.cad_checkin_router import (
    cad_checkin_router,
    get_checkin_manager,
)
from yuantus.security.auth.database import get_identity_db


def _current_user():
    return SimpleNamespace(
        id=7,
        roles=["admin"],
        is_superuser=False,
        tenant_id="tenant-1",
        org_id="org-1",
    )


def _client_with_status_data(item=None, version=None, native_file=None, jobs=None):
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def db_get(model, identity):
        if model is Item:
            return item if item is not None and getattr(item, "id", None) == identity else None
        if model is ItemVersion:
            return (
                version
                if version is not None and getattr(version, "id", None) == identity
                else None
            )
        if model is FileContainer:
            return (
                native_file
                if native_file is not None and getattr(native_file, "id", None) == identity
                else None
            )
        return None

    query_result = MagicMock()
    query_result.filter.return_value.order_by.return_value.all.return_value = jobs or []
    query_result.order_by.return_value.limit.return_value.all.return_value = jobs or []
    mock_db.get.side_effect = db_get
    mock_db.query.return_value = query_result

    app = FastAPI()
    app.include_router(cad_checkin_router, prefix="/api/v1")

    @app.get("/api/v1/file/{file_id}/conversion_summary", name="get_file_conversion_summary")
    def _conversion_summary(file_id: str):
        return {"file_id": file_id}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app), mock_db


def _make_item(item_id: str = "item-1", current_version_id: str = "ver-1"):
    return SimpleNamespace(
        id=item_id,
        current_version_id=current_version_id,
        item_type_id="Part",
        state="released",
        properties={},
    )


def _make_version(
    version_id: str = "ver-1",
    item_id: str = "item-1",
    native_file_id: str = "file-1",
):
    return SimpleNamespace(
        id=version_id,
        item_id=item_id,
        generation=1,
        is_current=True,
        properties={"native_file": native_file_id} if native_file_id else {},
    )


def _make_file(file_id: str = "file-1"):
    return SimpleNamespace(
        id=file_id,
        filename="part.stp",
        file_type="stp",
        system_path=f"/vault/{file_id}/part.stp",
        is_native_cad=True,
    )


def _make_job(job_id: str, status: str, task_type: str = "cad_geometry", item_id: str = "item-1", version_id: str = "ver-1", file_id: str = "file-1"):
    return SimpleNamespace(
        id=job_id,
        status=status,
        task_type=task_type,
        created_at=None,
        payload={
            "item_id": item_id,
            "version_id": version_id,
            "file_id": file_id,
        },
    )


def test_cad_checkin_status_route_registered_in_create_app():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/cad/{item_id}/checkin-status" in paths


def test_cad_checkin_status_happy_path_exposes_identity_and_aggregation():
    item = _make_item()
    version = _make_version()
    native_file = _make_file()
    jobs = [
        _make_job("job-pending", "pending"),
        _make_job("job-processing", "processing"),
        _make_job("job-completed", "completed"),
        _make_job("job-failed", "failed"),
        _make_job("job-completed-2", "completed"),
    ]

    client, _db = _client_with_status_data(
        item=item,
        version=version,
        native_file=native_file,
        jobs=jobs,
    )

    with patch(
        "yuantus.meta_engine.web.cad_checkin_router.CADConverterService.assess_viewer_readiness",
        return_value={"viewer_mode": "processing", "is_viewer_ready": False},
    ):
        resp = client.get("/api/v1/cad/item-1/checkin-status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["item_id"] == "item-1"
    assert body["file_id"] == "file-1"
    assert body["version_id"] == "ver-1"
    assert body["file_status_url"].endswith("/api/v1/file/file-1/conversion_summary")
    assert body["conversion_jobs_summary"] == {
        "pending": 1,
        "processing": 1,
        "completed": 2,
        "failed": 1,
        "total": 5,
    }
    assert body["viewer_readiness"]["viewer_mode"] == "processing"


def test_cad_checkin_status_prefers_anchored_job_ids_over_unrelated_jobs():
    item = _make_item()
    version = _make_version()
    version.properties["cad_conversion_job_ids"] = ["job-target"]
    native_file = _make_file()
    jobs = [
        _make_job("job-target", "completed"),
        _make_job(
            "job-unrelated",
            "failed",
            item_id="item-else",
            version_id="ver-else",
            file_id="file-else",
        ),
    ]

    client, _db = _client_with_status_data(
        item=item,
        version=version,
        native_file=native_file,
        jobs=jobs,
    )

    with patch(
        "yuantus.meta_engine.web.cad_checkin_router.CADConverterService.assess_viewer_readiness",
        return_value={"viewer_mode": "geometry_only", "is_viewer_ready": True},
    ):
        resp = client.get("/api/v1/cad/item-1/checkin-status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["conversion_job_ids"] == ["job-target"]
    assert body["conversion_jobs_summary"] == {
        "pending": 0,
        "processing": 0,
        "completed": 1,
        "failed": 0,
        "total": 1,
    }
    assert [job["id"] for job in body["conversion_jobs"]] == ["job-target"]


@pytest.mark.parametrize(
    ("label", "item", "version", "native_file"),
    [
        ("item", None, None, None),
        ("version", _make_item(current_version_id="ver-missing"), None, None),
        (
            "native_file",
            _make_item(),
            _make_version(native_file_id="file-missing"),
            None,
        ),
    ],
)
def test_cad_checkin_status_missing_links_return_404(label, item, version, native_file):
    client, _db = _client_with_status_data(
        item=item,
        version=version,
        native_file=native_file,
        jobs=[],
    )

    resp = client.get("/api/v1/cad/item-1/checkin-status")

    assert resp.status_code == 404, label
    detail = str(resp.json().get("detail", "")).lower()
    assert "not found" in detail or "missing" in detail


def test_checkin_route_returns_status_url_and_job_ids():
    mock_mgr = MagicMock()
    checked_in_version = SimpleNamespace(
        id="ver-1",
        generation=1,
        properties={
            "native_file": "file-1",
            "cad_conversion_job_ids": ["job-preview", "job-geometry"],
        },
    )
    mock_mgr.checkin.return_value = checked_in_version
    mock_mgr.session = MagicMock()

    mock_identity_db = MagicMock()

    def override_mgr():
        return mock_mgr

    def override_identity_db():
        try:
            yield mock_identity_db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_checkin_router, prefix="/api/v1")

    @app.get("/api/v1/file/{file_id}/conversion_summary", name="get_file_conversion_summary")
    def _conversion_summary(file_id: str):
        return {"file_id": file_id}

    app.dependency_overrides[get_checkin_manager] = override_mgr
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_identity_db] = override_identity_db

    with patch(
        "yuantus.meta_engine.web.cad_checkin_router.QuotaService.evaluate",
        return_value=[],
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/cad/item-1/checkin",
            files={"file": ("part.stp", b"cad-bytes", "application/octet-stream")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["item_id"] == "item-1"
    assert body["version_id"] == "ver-1"
    assert body["file_id"] == "file-1"
    assert body["conversion_job_ids"] == ["job-preview", "job-geometry"]
    assert body["status_url"].endswith("/api/v1/cad/item-1/checkin-status")
    assert body["file_status_url"].endswith("/api/v1/file/file-1/conversion_summary")
