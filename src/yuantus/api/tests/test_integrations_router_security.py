from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user_id
from yuantus.api.routers.integrations import router as integrations_router


def _make_client(*, authenticated: bool) -> TestClient:
    app = FastAPI()
    app.include_router(integrations_router, prefix="/api/v1")

    if authenticated:
        app.dependency_overrides[get_current_user_id] = lambda: 7
    else:
        def _unauthorized() -> int:
            raise HTTPException(status_code=401, detail="Unauthorized")

        app.dependency_overrides[get_current_user_id] = _unauthorized

    return TestClient(app)


def _mock_client(name: str, *, health_result=None, health_exc: Exception | None = None):
    client = MagicMock()
    client.base_url = f"http://internal-{name}.service.local"
    if health_exc is not None:
        client.health = AsyncMock(side_effect=health_exc)
    else:
        client.health = AsyncMock(return_value=health_result or {"service": name, "ok": True})
    return client


def test_integrations_health_requires_authentication() -> None:
    client = _make_client(authenticated=False)

    response = client.get("/api/v1/integrations/health")

    assert response.status_code == 401


def test_integrations_health_returns_sanitized_service_status_when_authenticated() -> None:
    client = _make_client(authenticated=True)
    athena = _mock_client("athena")
    cad_ml = _mock_client("cad-ml")
    dedup = _mock_client("dedup")

    with patch(
        "yuantus.api.routers.integrations.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ), patch(
        "yuantus.api.routers.integrations.AthenaClient", return_value=athena
    ), patch(
        "yuantus.api.routers.integrations.CadMLClient", return_value=cad_ml
    ), patch(
        "yuantus.api.routers.integrations.DedupVisionClient", return_value=dedup
    ):
        response = client.get(
            "/api/v1/integrations/health",
            headers={
                "Authorization": "Bearer outer-token",
                "X-Athena-Authorization": "Bearer athena-token",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tenant_id"] == "tenant-1"
    assert body["org_id"] == "org-1"
    assert body["services"]["athena"] == {"ok": True, "detail": {"service": "athena", "ok": True}}
    assert "base_url" not in body["services"]["athena"]
    athena.health.assert_awaited_once_with(
        authorization=None, athena_authorization="Bearer athena-token"
    )
    cad_ml.health.assert_awaited_once_with(authorization="Bearer outer-token")
    dedup.health.assert_awaited_once_with(authorization="Bearer outer-token")


def test_integrations_health_redacts_upstream_http_error_details() -> None:
    client = _make_client(authenticated=True)
    request = httpx.Request("GET", "http://internal-athena.service.local/health")
    response = httpx.Response(
        502,
        request=request,
        text='{"detail":"secret upstream stack trace"}',
    )
    exc = httpx.HTTPStatusError("bad gateway", request=request, response=response)

    with patch(
        "yuantus.api.routers.integrations.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ), patch(
        "yuantus.api.routers.integrations.AthenaClient",
        return_value=_mock_client("athena", health_exc=exc),
    ), patch(
        "yuantus.api.routers.integrations.CadMLClient",
        return_value=_mock_client("cad-ml"),
    ), patch(
        "yuantus.api.routers.integrations.DedupVisionClient",
        return_value=_mock_client("dedup"),
    ):
        response = client.get("/api/v1/integrations/health")

    assert response.status_code == 200
    athena_payload = response.json()["services"]["athena"]
    assert athena_payload == {
        "ok": False,
        "error_code": "upstream_http_error",
        "status_code": 502,
        "error_type": "HTTPStatusError",
        "summary": "upstream returned HTTP 502 (HTTPStatusError)",
    }
    assert "secret upstream stack trace" not in response.text
    assert "internal-athena.service.local" not in response.text


def test_integrations_health_redacts_upstream_request_error_details() -> None:
    client = _make_client(authenticated=True)
    request = httpx.Request("GET", "http://internal-cad-ml.service.local/api/v1/health")
    exc = httpx.ConnectTimeout("connect timeout", request=request)

    with patch(
        "yuantus.api.routers.integrations.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ), patch(
        "yuantus.api.routers.integrations.AthenaClient",
        return_value=_mock_client("athena"),
    ), patch(
        "yuantus.api.routers.integrations.CadMLClient",
        return_value=_mock_client("cad-ml", health_exc=exc),
    ), patch(
        "yuantus.api.routers.integrations.DedupVisionClient",
        return_value=_mock_client("dedup"),
    ):
        response = client.get("/api/v1/integrations/health")

    assert response.status_code == 200
    cad_ml_payload = response.json()["services"]["cad_ml"]
    assert cad_ml_payload == {
        "ok": False,
        "error_code": "upstream_request_error",
        "error_type": "ConnectTimeout",
        "summary": "upstream request failed (ConnectTimeout)",
    }
    assert "internal-cad-ml.service.local" not in response.text
