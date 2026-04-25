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


def test_summary_appends_meta():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_summary_search_router.ReportService") as svc_cls:
        with patch(
            "yuantus.meta_engine.web.report_summary_search_router.get_request_context"
        ) as ctx_fn:
            with patch("yuantus.meta_engine.web.report_summary_search_router.get_settings") as settings_fn:
                svc_cls.return_value.get_summary.return_value = {"total_reports": 3}
                ctx_fn.return_value = SimpleNamespace(tenant_id="tenant-1", org_id="org-1")
                settings_fn.return_value = SimpleNamespace(TENANCY_MODE="scoped")

                resp = client.get("/api/v1/reports/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_reports"] == 3
    assert body["meta"]["tenant_id"] == "tenant-1"
    assert body["meta"]["org_id"] == "org-1"
    assert body["meta"]["tenancy_mode"] == "scoped"
    assert "generated_at" in body["meta"]


def test_advanced_search_forwards_filters_and_pagination():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_summary_search_router.AdvancedSearchService") as svc_cls:
        svc = svc_cls.return_value
        svc.search.return_value = {"items": [], "total": 0}
        resp = client.post(
            "/api/v1/reports/search",
            json={
                "item_type_id": "part",
                "filters": [{"field": "state", "op": "eq", "value": "Released"}],
                "sort": [{"field": "name", "direction": "asc"}],
                "page": 2,
                "page_size": 50,
                "include_count": False,
            },
        )

    assert resp.status_code == 200
    svc.search.assert_called_once_with(
        item_type_id="part",
        filters=[{"field": "state", "op": "eq", "value": "Released"}],
        full_text=None,
        sort=[{"field": "name", "direction": "asc"}],
        columns=None,
        lang=None,
        fallback_langs=None,
        localized_fields=None,
        page=2,
        page_size=50,
        include_count=False,
    )
