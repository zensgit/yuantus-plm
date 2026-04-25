from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client_with_user(user):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def _dashboard(**overrides):
    payload = {
        "id": "dash-1",
        "name": "Ops",
        "description": None,
        "layout": None,
        "widgets": None,
        "auto_refresh": False,
        "refresh_interval": 300,
        "owner_id": 1,
        "is_public": False,
        "is_default": False,
        "created_at": None,
        "created_by_id": 1,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_create_dashboard_sets_owner_and_creator():
    user = SimpleNamespace(id=9, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    created = _dashboard(owner_id=9, created_by_id=9)
    with patch("yuantus.meta_engine.web.report_dashboard_router.DashboardService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_dashboard.return_value = created
        resp = client.post("/api/v1/reports/dashboards", json={"name": "Ops Board"})

    assert resp.status_code == 200
    svc.create_dashboard.assert_called_once()
    assert svc.create_dashboard.call_args.kwargs["owner_id"] == 9
    assert svc.create_dashboard.call_args.kwargs["created_by_id"] == 9


def test_get_dashboard_denies_private_non_owner():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_dashboard_router.DashboardService") as svc_cls:
        svc_cls.return_value.get_dashboard.return_value = _dashboard(owner_id=1, is_public=False)
        resp = client.get("/api/v1/reports/dashboards/dash-1")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied"


def test_delete_dashboard_owner_calls_service():
    user = SimpleNamespace(id=1, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_dashboard_router.DashboardService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_dashboard.return_value = _dashboard(owner_id=1)
        resp = client.delete("/api/v1/reports/dashboards/dash-1")

    assert resp.status_code == 200
    assert resp.json() == {"status": "deleted", "id": "dash-1"}
    svc.delete_dashboard.assert_called_once_with("dash-1")
