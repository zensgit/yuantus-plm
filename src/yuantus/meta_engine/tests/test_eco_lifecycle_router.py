from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db


@pytest.fixture(autouse=True)
def _auth_optional(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client():
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = lambda: 1
    return TestClient(app), mock_db


def test_cancel_endpoint_commits_and_returns_eco():
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_lifecycle_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.action_cancel.return_value = SimpleNamespace(
            to_dict=lambda: {"id": "eco-1", "state": "canceled"}
        )
        resp = client.post(
            "/api/v1/eco/eco-1/cancel",
            params={"reason": "duplicate change"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"id": "eco-1", "state": "canceled"}
    assert db.commit.called
    service.action_cancel.assert_called_once_with("eco-1", 1, "duplicate change")


def test_cancel_endpoint_value_error_maps_to_400():
    client, _db = _client()

    with patch("yuantus.meta_engine.web.eco_lifecycle_router.ECOService") as service_cls:
        service_cls.return_value.action_cancel.side_effect = ValueError(
            "Cannot cancel done ECO"
        )
        resp = client.post("/api/v1/eco/eco-1/cancel")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Cannot cancel done ECO"


def test_move_stage_endpoint_commits_and_returns_eco():
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_lifecycle_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.move_to_stage.return_value = SimpleNamespace(
            to_dict=lambda: {
                "id": "eco-1",
                "stage_id": "stage-2",
            }
        )
        resp = client.post(
            "/api/v1/eco/eco-1/move-stage",
            json={"stage_id": "stage-2"},
        )

    assert resp.status_code == 200
    assert resp.json()["stage_id"] == "stage-2"
    assert db.commit.called
    service.move_to_stage.assert_called_once_with("eco-1", "stage-2", 1)


def test_move_stage_endpoint_value_error_maps_to_400():
    client, _db = _client()

    with patch("yuantus.meta_engine.web.eco_lifecycle_router.ECOService") as service_cls:
        service_cls.return_value.move_to_stage.side_effect = ValueError(
            "Target stage not found"
        )
        resp = client.post(
            "/api/v1/eco/eco-1/move-stage",
            json={"stage_id": "missing-stage"},
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Target stage not found"
