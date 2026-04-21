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
    """These tests override route auth dependency; middleware auth is out of scope."""
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


def test_export_definition_denies_when_role_not_allowed():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    report = SimpleNamespace(
        id="rep-1",
        owner_id=1,
        is_public=True,
        allowed_roles=["admin"],
    )

    with patch("yuantus.meta_engine.web.report_router.ReportDefinitionService") as svc_cls:
        svc_cls.return_value.get_definition.return_value = report
        resp = client.post("/api/v1/reports/definitions/rep-1/export", json={})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied"


def test_advanced_search_passes_report_language_selection():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_router.AdvancedSearchService") as svc_cls:
        svc = svc_cls.return_value
        svc.search.return_value = {"items": [], "total": 0}
        resp = client.post(
            "/api/v1/reports/search",
            json={
                "columns": ["name", "description"],
                "lang": "zh_CN",
                "fallback_langs": ["en_US"],
                "localized_fields": ["description"],
            },
        )

    assert resp.status_code == 200
    svc.search.assert_called_once_with(
        item_type_id=None,
        filters=None,
        full_text=None,
        sort=None,
        columns=["name", "description"],
        lang="zh_CN",
        fallback_langs=["en_US"],
        localized_fields=["description"],
        page=1,
        page_size=25,
        include_count=True,
    )


def test_export_definition_allows_superuser_without_admin_role():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=True)
    client = _client_with_user(user)

    report = SimpleNamespace(
        id="rep-1",
        owner_id=1,
        is_public=False,
        allowed_roles=None,
    )

    with patch("yuantus.meta_engine.web.report_router.ReportDefinitionService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_definition.return_value = report
        svc.export_definition.return_value = {
            "content": b"id,name\n",
            "media_type": "text/csv",
            "extension": "csv",
        }
        resp = client.post("/api/v1/reports/definitions/rep-1/export", json={})

    assert resp.status_code == 200
    assert "attachment; filename=\"report_rep-1.csv\"" == resp.headers["content-disposition"]
    svc.export_definition.assert_called_once()


def test_export_definition_allows_case_insensitive_allowed_roles():
    user = SimpleNamespace(id=2, roles=["Viewer"], is_superuser=False)
    client = _client_with_user(user)

    report = SimpleNamespace(
        id="rep-1",
        owner_id=1,
        is_public=True,
        allowed_roles=[" viewer "],
    )

    with patch("yuantus.meta_engine.web.report_router.ReportDefinitionService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_definition.return_value = report
        svc.export_definition.return_value = {
            "content": b"id,name\n",
            "media_type": "text/csv",
            "extension": "csv",
        }
        resp = client.post("/api/v1/reports/definitions/rep-1/export", json={})

    assert resp.status_code == 200
    assert "attachment; filename=\"report_rep-1.csv\"" == resp.headers["content-disposition"]
    svc.export_definition.assert_called_once()
