from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
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
    return TestClient(app), mock_db


def test_get_bom_changes_404_when_eco_missing():
    client, _db = _client()

    with patch(
        "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
    ) as service_cls:
        service_cls.return_value.get_eco.return_value = None
        resp = client.get("/api/v1/eco/eco-404/changes")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "ECO not found"


def test_get_bom_changes_returns_to_dict_list():
    client, _db = _client()
    change = SimpleNamespace(
        to_dict=lambda: {
            "id": "chg-1",
            "eco_id": "eco-1",
            "change_type": "update",
        }
    )

    with patch(
        "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
    ) as service_cls:
        service = service_cls.return_value
        service.get_eco.return_value = SimpleNamespace(id="eco-1")
        service.get_bom_changes.return_value = [change]
        resp = client.get("/api/v1/eco/eco-1/changes")

    assert resp.status_code == 200
    assert resp.json() == [
        {"id": "chg-1", "eco_id": "eco-1", "change_type": "update"}
    ]
    service.get_bom_changes.assert_called_once_with("eco-1")


def test_conflicts_returns_service_payload():
    client, _db = _client()
    payload = [
        {
            "type": "routing",
            "operation_id": "op-1",
            "reason": "concurrent_routing_modification",
        }
    ]

    with patch(
        "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
    ) as service_cls:
        service_cls.return_value.detect_rebase_conflicts.return_value = payload
        resp = client.get("/api/v1/eco/eco-1/conflicts")

    assert resp.status_code == 200
    assert resp.json() == payload
    service_cls.return_value.detect_rebase_conflicts.assert_called_once_with("eco-1")


def test_conflicts_value_error_maps_to_404():
    client, _db = _client()

    with patch(
        "yuantus.meta_engine.web.eco_change_analysis_router.ECOService"
    ) as service_cls:
        service_cls.return_value.detect_rebase_conflicts.side_effect = ValueError(
            "ECO not found"
        )
        resp = client.get("/api/v1/eco/eco-404/conflicts")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "ECO not found"
