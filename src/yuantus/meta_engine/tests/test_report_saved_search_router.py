from __future__ import annotations

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


def test_create_saved_search_returns_response_payload():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)
    saved = SimpleNamespace(
        id="ss-1",
        name="My Search",
        description="desc",
        owner_id=7,
        is_public=False,
        item_type_id="part",
        criteria={"status": "released"},
        display_columns=["name"],
        page_size=25,
        use_count=0,
        last_used_at=None,
        created_at=None,
        updated_at=None,
    )

    with patch("yuantus.meta_engine.web.report_saved_search_router.SavedSearchService") as svc_cls:
        svc_cls.return_value.create_saved_search.return_value = saved
        resp = client.post(
            "/api/v1/reports/saved-searches",
            json={"name": "My Search", "criteria": {"status": "released"}},
        )

    assert resp.status_code == 200
    assert resp.json()["id"] == "ss-1"


def test_list_saved_searches_passes_include_public_flag():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_saved_search_router.SavedSearchService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_saved_searches.return_value = []
        resp = client.get("/api/v1/reports/saved-searches", params={"include_public": "false"})

    assert resp.status_code == 200
    svc.list_saved_searches.assert_called_once_with(owner_id=7, include_public=False)


def test_get_saved_search_404_when_missing():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    with patch("yuantus.meta_engine.web.report_saved_search_router.SavedSearchService") as svc_cls:
        svc_cls.return_value.get_saved_search.return_value = None
        resp = client.get("/api/v1/reports/saved-searches/ss-missing")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Saved search not found"


def test_get_saved_search_denies_private_non_owner():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)
    saved = SimpleNamespace(owner_id=8, is_public=False)

    with patch("yuantus.meta_engine.web.report_saved_search_router.SavedSearchService") as svc_cls:
        svc_cls.return_value.get_saved_search.return_value = saved
        resp = client.get("/api/v1/reports/saved-searches/ss-1")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied"


def test_update_saved_search_denies_non_owner():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)
    saved = SimpleNamespace(owner_id=8)

    with patch("yuantus.meta_engine.web.report_saved_search_router.SavedSearchService") as svc_cls:
        svc_cls.return_value.get_saved_search.return_value = saved
        resp = client.patch("/api/v1/reports/saved-searches/ss-1", json={"name": "New"})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied"


def test_delete_saved_search_owner_can_delete():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)
    saved = SimpleNamespace(owner_id=7)

    with patch("yuantus.meta_engine.web.report_saved_search_router.SavedSearchService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_saved_search.return_value = saved
        resp = client.delete("/api/v1/reports/saved-searches/ss-1")

    assert resp.status_code == 200
    assert resp.json() == {"status": "deleted", "id": "ss-1"}
    svc.delete_saved_search.assert_called_once_with("ss-1")


def test_run_saved_search_forwards_zero_page_size_as_none():
    user = SimpleNamespace(id=7, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)
    saved = SimpleNamespace(owner_id=7, is_public=False)

    with patch("yuantus.meta_engine.web.report_saved_search_router.SavedSearchService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_saved_search.return_value = saved
        svc.run_saved_search.return_value = {"items": [], "total": 0}
        resp = client.post("/api/v1/reports/saved-searches/ss-1/run", params={"page": 2, "page_size": 0})

    assert resp.status_code == 200
    svc.run_saved_search.assert_called_once_with("ss-1", page=2, page_size=None)
