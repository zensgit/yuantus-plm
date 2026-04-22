from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import require_admin_user
from yuantus.config.settings import Settings
from yuantus.meta_engine.web.cad_connectors_router import cad_connectors_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(cad_connectors_router, prefix="/api/v1")
    app.dependency_overrides[require_admin_user] = lambda: SimpleNamespace(
        id=1,
        roles=["admin"],
        is_superuser=True,
        tenant_id="tenant-1",
        org_id="org-1",
    )
    return TestClient(app)


def _connector(
    connector_id: str,
    *,
    label: str | None = None,
    cad_format: str = "STEP",
    document_type: str = "3d",
    extensions: list[str] | None = None,
):
    return SimpleNamespace(
        id=connector_id,
        label=label or connector_id.upper(),
        cad_format=cad_format,
        document_type=document_type,
        extensions=extensions or ["step", "stp"],
        aliases=[connector_id.upper()],
        priority=10,
        description=f"{connector_id} connector",
    )


def test_list_cad_connectors_returns_sorted_connector_metadata() -> None:
    client = _client()
    connectors = [
        _connector("step"),
        _connector("dxf", cad_format="DXF", document_type="2d", extensions=["dxf"]),
    ]

    with patch(
        "yuantus.meta_engine.web.cad_connectors_router.cad_registry.list",
        return_value=connectors,
    ):
        response = client.get("/api/v1/cad/connectors")

    assert response.status_code == 200
    body = response.json()
    assert [entry["id"] for entry in body] == ["dxf", "step"]
    assert body[0] == {
        "id": "dxf",
        "label": "DXF",
        "cad_format": "DXF",
        "document_type": "2d",
        "extensions": ["dxf"],
        "aliases": ["DXF"],
        "priority": 10,
        "description": "dxf connector",
    }


def test_reload_cad_connectors_accepts_inline_config_payload() -> None:
    client = _client()
    settings = Settings(
        _env_file=None,
        CAD_CONNECTORS_CONFIG_PATH="/etc/yuantus/cad-connectors.json",
        CAD_CONNECTORS_ALLOW_PATH_OVERRIDE=False,
    )
    result = SimpleNamespace(entries=[object(), object()], errors=["warning"])

    with patch(
        "yuantus.meta_engine.web.cad_connectors_router.get_settings",
        return_value=settings,
    ):
        with patch(
            "yuantus.meta_engine.web.cad_connectors_router.reload_connectors",
            return_value=result,
        ) as reload_fn:
            response = client.post(
                "/api/v1/cad/connectors/reload",
                json={"config": {"connectors": []}},
            )

    assert response.status_code == 200
    assert response.json() == {
        "config_path": "/etc/yuantus/cad-connectors.json",
        "custom_loaded": 2,
        "errors": ["warning"],
    }
    reload_fn.assert_called_once_with(config_payload={"connectors": []})


def test_reload_cad_connectors_rejects_path_override_when_disabled() -> None:
    client = _client()
    settings = Settings(
        _env_file=None,
        CAD_CONNECTORS_ALLOW_PATH_OVERRIDE=False,
    )

    with patch(
        "yuantus.meta_engine.web.cad_connectors_router.get_settings",
        return_value=settings,
    ):
        with patch(
            "yuantus.meta_engine.web.cad_connectors_router.reload_connectors"
        ) as reload_fn:
            response = client.post(
                "/api/v1/cad/connectors/reload",
                json={"config_path": "/tmp/custom-connectors.json"},
            )

    assert response.status_code == 403
    assert "Path override disabled" in response.json()["detail"]
    reload_fn.assert_not_called()


def test_reload_cad_connectors_accepts_path_override_when_enabled() -> None:
    client = _client()
    settings = Settings(
        _env_file=None,
        CAD_CONNECTORS_ALLOW_PATH_OVERRIDE=True,
    )
    result = SimpleNamespace(entries=[object()], errors=[])

    with patch(
        "yuantus.meta_engine.web.cad_connectors_router.get_settings",
        return_value=settings,
    ):
        with patch(
            "yuantus.meta_engine.web.cad_connectors_router.reload_connectors",
            return_value=result,
        ) as reload_fn:
            response = client.post(
                "/api/v1/cad/connectors/reload",
                json={"config_path": "/tmp/custom-connectors.json"},
            )

    assert response.status_code == 200
    assert response.json() == {
        "config_path": "/tmp/custom-connectors.json",
        "custom_loaded": 1,
        "errors": [],
    }
    reload_fn.assert_called_once_with(config_path="/tmp/custom-connectors.json")
