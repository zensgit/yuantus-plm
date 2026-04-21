from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user, require_admin_user
from yuantus.database import get_db
from yuantus.meta_engine.web.permission_router import permission_router
from yuantus.meta_engine.web.schema_router import schema_router
from yuantus.meta_engine.web.search_router import search_router


def _current_user(*, roles: list[str], is_superuser: bool = False) -> CurrentUser:
    return CurrentUser(
        id=1,
        tenant_id="tenant-1",
        org_id="org-1",
        username="tester",
        email="tester@example.com",
        roles=roles,
        is_superuser=is_superuser,
    )


def _client(router, user: CurrentUser) -> tuple[TestClient, MagicMock]:
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), mock_db


def test_require_admin_user_allows_admin_role() -> None:
    user = _current_user(roles=["admin"])

    assert require_admin_user(user) is user


def test_require_admin_user_allows_superuser_flag_without_roles() -> None:
    user = _current_user(roles=["viewer"], is_superuser=True)

    assert require_admin_user(user) is user


def test_require_admin_user_rejects_non_admin() -> None:
    user = _current_user(roles=["viewer"])

    with pytest.raises(HTTPException) as exc_info:
        require_admin_user(user)

    assert getattr(exc_info.value, "status_code", None) == 403
    assert getattr(exc_info.value, "detail", None) == "Admin role required"


def test_search_status_requires_admin_via_shared_dependency() -> None:
    client, _ = _client(search_router, _current_user(roles=["viewer"]))

    response = client.get("/api/v1/search/status")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_search_status_allows_admin_via_shared_dependency() -> None:
    client, _ = _client(search_router, _current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.status.return_value = {
            "engine": "noop",
            "enabled": False,
            "index": "items",
            "index_exists": False,
        }
        response = client.get("/api/v1/search/status")

    assert response.status_code == 200
    assert response.json()["engine"] == "noop"


def test_permission_list_requires_admin_via_shared_dependency() -> None:
    client, _ = _client(permission_router, _current_user(roles=["viewer"]))

    response = client.get("/api/v1/meta/permissions")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_schema_create_requires_admin_via_shared_dependency() -> None:
    client, _ = _client(schema_router, _current_user(roles=["viewer"]))

    response = client.post(
        "/api/v1/meta/item-types",
        json={"id": "Part", "label": "Part"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"
