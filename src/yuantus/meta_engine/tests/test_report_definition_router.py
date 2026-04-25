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


def _report(**overrides):
    payload = {
        "id": "rep-1",
        "name": "A",
        "code": "RPT",
        "description": None,
        "category": None,
        "report_type": "table",
        "data_source": {"kind": "items"},
        "layout": None,
        "parameters": None,
        "owner_id": 1,
        "is_public": False,
        "allowed_roles": None,
        "is_active": True,
        "created_at": None,
        "created_by_id": 1,
        "updated_at": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_create_report_definition_sets_owner_and_creator():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    created = _report(owner_id=7, created_by_id=7)
    with patch("yuantus.meta_engine.web.report_definition_router.ReportDefinitionService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_definition.return_value = created
        resp = client.post(
            "/api/v1/reports/definitions",
            json={"name": "My Report", "data_source": {"kind": "items"}},
        )

    assert resp.status_code == 200
    svc.create_definition.assert_called_once()
    assert svc.create_definition.call_args.kwargs["owner_id"] == 7
    assert svc.create_definition.call_args.kwargs["created_by_id"] == 7


def test_export_report_definition_invalid_format_returns_400():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_definition_router.ReportDefinitionService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_definition.return_value = _report(owner_id=2)
        svc.export_definition.side_effect = ValueError("unsupported export format")
        resp = client.post(
            "/api/v1/reports/definitions/rep-1/export",
            json={"export_format": "xlsx"},
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "unsupported export format"


def test_list_report_executions_non_admin_scopes_to_current_user_without_report_filter():
    user = SimpleNamespace(id=5, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_definition_router.ReportDefinitionService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_executions.return_value = []
        resp = client.get("/api/v1/reports/executions?status=done&limit=5&offset=2")

    assert resp.status_code == 200
    svc.list_executions.assert_called_once_with(
        report_id=None,
        executed_by_id=5,
        status="done",
        limit=5,
        offset=2,
    )


def test_get_report_execution_denies_when_user_is_not_owner_or_executor():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    execution = SimpleNamespace(id="exe-1", report_id="rep-1", executed_by_id=3)
    public_report = _report(owner_id=1, is_public=True, allowed_roles=None)

    with patch("yuantus.meta_engine.web.report_definition_router.ReportDefinitionService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_execution.return_value = execution
        svc.get_definition.return_value = public_report
        resp = client.get("/api/v1/reports/executions/exe-1")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied"
