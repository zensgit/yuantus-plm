from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import get_db


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    """These tests override route dependencies; middleware auth is out of scope."""
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), mock_db_session


def test_add_effectivity_uses_effectivity_router_service_and_commits():
    client, db = _client()

    with patch("yuantus.meta_engine.web.version_effectivity_router.VersionService") as svc_cls:
        svc_cls.return_value.add_date_effectivity.return_value = {"id": "eff-1"}
        resp = client.post(
            "/api/v1/versions/ver-1/effectivity",
            json={
                "start_date": "2026-04-24T00:00:00",
                "end_date": "2026-05-01T00:00:00",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"id": "eff-1"}
    svc_cls.return_value.add_date_effectivity.assert_called_once_with(
        "ver-1",
        datetime(2026, 4, 24, 0, 0),
        datetime(2026, 5, 1, 0, 0),
    )
    assert db.commit.called


def test_effective_version_route_returns_404_when_none_effective():
    client, _db = _client()

    with patch("yuantus.meta_engine.web.version_effectivity_router.VersionService") as svc_cls:
        svc_cls.return_value.find_effective_version.return_value = None
        resp = client.get("/api/v1/versions/items/item-1/effective")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No effective version found"


def test_version_tree_route_uses_effectivity_router_service():
    client, _db = _client()

    with patch("yuantus.meta_engine.web.version_effectivity_router.VersionService") as svc_cls:
        svc_cls.return_value.get_version_tree.return_value = [
            {"id": "ver-1", "children": []}
        ]
        resp = client.get("/api/v1/versions/items/item-1/tree")

    assert resp.status_code == 200
    assert resp.json() == [{"id": "ver-1", "children": []}]
    svc_cls.return_value.get_version_tree.assert_called_once_with("item-1")
