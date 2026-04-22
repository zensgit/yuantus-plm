from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.cad_backend_profile_service import (
    CadBackendProfileResolution,
)
from yuantus.meta_engine.web.cad_backend_profile_router import cad_backend_profile_router


def _client(user: SimpleNamespace) -> tuple[TestClient, MagicMock]:
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_backend_profile_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), mock_db


def _resolution(
    *,
    configured: str = "hybrid-auto",
    effective: str = "hybrid-auto",
    source: str = "plugin-config:tenant-org",
    scope: dict | None = None,
) -> CadBackendProfileResolution:
    return CadBackendProfileResolution(
        configured=configured,
        effective=effective,
        source=source,
        options=["local-baseline", "hybrid-auto", "external-enterprise"],
        scope=scope
        or {"tenant_id": "tenant-1", "org_id": "org-1", "level": "tenant-org"},
    )


def test_get_backend_profile_returns_current_resolution() -> None:
    client, _ = _client(SimpleNamespace(id=1, roles=["engineer"]))

    with patch(
        "yuantus.meta_engine.web.cad_backend_profile_router.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ):
        with patch(
            "yuantus.meta_engine.web.cad_backend_profile_router.CadBackendProfileService"
        ) as svc_cls:
            svc_cls.return_value.resolve.return_value = _resolution()
            response = client.get("/api/v1/cad/backend-profile")

    assert response.status_code == 200
    assert response.json() == {
        "configured": "hybrid-auto",
        "effective": "hybrid-auto",
        "source": "plugin-config:tenant-org",
        "options": ["local-baseline", "hybrid-auto", "external-enterprise"],
        "scope": {"tenant_id": "tenant-1", "org_id": "org-1", "level": "tenant-org"},
    }


def test_put_backend_profile_updates_tenant_scope() -> None:
    client, _ = _client(SimpleNamespace(id=1, roles=["admin"]))

    with patch(
        "yuantus.meta_engine.web.cad_backend_profile_router.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ):
        with patch(
            "yuantus.meta_engine.web.cad_backend_profile_router.CadBackendProfileService"
        ) as svc_cls:
            svc_cls.return_value.update_override.return_value = _resolution(
                source="plugin-config:tenant-default",
                scope={"tenant_id": "tenant-1", "org_id": None, "level": "tenant-default"},
            )
            response = client.put(
                "/api/v1/cad/backend-profile",
                json={"profile": "hybrid-auto", "scope": "tenant"},
            )

    assert response.status_code == 200
    svc_cls.return_value.update_override.assert_called_once_with(
        tenant_id="tenant-1",
        org_id="org-1",
        user_id=1,
        profile="hybrid-auto",
        scope="tenant",
    )


def test_put_backend_profile_requires_admin() -> None:
    client, _ = _client(SimpleNamespace(id=2, roles=["viewer"]))
    response = client.put(
        "/api/v1/cad/backend-profile",
        json={"profile": "hybrid-auto", "scope": "tenant"},
    )
    assert response.status_code == 403


def test_delete_backend_profile_requires_admin() -> None:
    client, _ = _client(SimpleNamespace(id=2, roles=["viewer"]))
    response = client.delete("/api/v1/cad/backend-profile?scope=org")
    assert response.status_code == 403
