from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.web.version_iteration_router import version_iteration_router


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    """These tests override route auth dependency; middleware auth is out of scope."""
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client_with_user_id(user_id: int = 7):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_user_id():
        return user_id

    app = FastAPI()
    app.include_router(version_iteration_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_get_user_id
    return TestClient(app), mock_db_session


def _iteration(**overrides):
    values = {
        "id": "it-1",
        "version_id": "ver-1",
        "iteration_number": 1,
        "iteration_label": "1",
        "is_latest": True,
        "source_type": "manual",
        "description": "draft save",
        "properties": {"color": "red"},
        "created_at": datetime(2026, 4, 24, 9, 0, 0),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_iteration_create_list_and_latest_endpoints_use_service_payloads():
    client, db = _client_with_user_id(7)
    iteration = _iteration()

    with patch("yuantus.meta_engine.web.version_iteration_router.IterationService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_iteration.return_value = iteration
        svc.get_iterations.return_value = [iteration]
        svc.get_latest_iteration.return_value = iteration

        create_response = client.post(
            "/api/v1/versions/ver-1/iterations",
            json={
                "properties": {"color": "red"},
                "description": "draft save",
                "source_type": "manual",
            },
        )
        list_response = client.get("/api/v1/versions/ver-1/iterations")
        latest_response = client.get("/api/v1/versions/ver-1/iterations/latest")

    assert create_response.status_code == 200
    assert create_response.json()["version_id"] == "ver-1"
    assert list_response.status_code == 200
    assert list_response.json()[0]["description"] == "draft save"
    assert latest_response.status_code == 200
    assert latest_response.json()["properties"] == {"color": "red"}
    svc.create_iteration.assert_called_once_with(
        version_id="ver-1",
        user_id=7,
        properties={"color": "red"},
        description="draft save",
        source_type="manual",
    )
    assert db.commit.call_count == 1


def test_latest_iteration_missing_maps_to_404():
    client, _db = _client_with_user_id()

    with patch("yuantus.meta_engine.web.version_iteration_router.IterationService") as svc_cls:
        svc_cls.return_value.get_latest_iteration.return_value = None
        response = client.get("/api/v1/versions/ver-1/iterations/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "No iterations found"


def test_iteration_restore_and_delete_endpoints_commit():
    client, db = _client_with_user_id(7)
    iteration = _iteration(is_latest=True)

    with patch("yuantus.meta_engine.web.version_iteration_router.IterationService") as svc_cls:
        svc = svc_cls.return_value
        svc.restore_iteration.return_value = iteration
        svc.delete_iteration.return_value = True

        restore_response = client.post("/api/v1/versions/iterations/it-1/restore")
        delete_response = client.delete("/api/v1/versions/iterations/it-1")

    assert restore_response.status_code == 200
    assert restore_response.json()["is_latest"] is True
    assert delete_response.status_code == 200
    assert delete_response.json() == {"status": "deleted"}
    svc.restore_iteration.assert_called_once_with("it-1", 7)
    svc.delete_iteration.assert_called_once_with("it-1")
    assert db.commit.call_count == 2
