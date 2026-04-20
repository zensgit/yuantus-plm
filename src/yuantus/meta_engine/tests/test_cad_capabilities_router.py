"""Router contract tests for consolidated CAD capabilities discovery."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.database import get_db
from yuantus.meta_engine.services.cad_backend_profile_service import (
    CadBackendProfileResolution,
)
from yuantus.meta_engine.web.cad_router import router as cad_router
from yuantus.meta_engine.web.file_router import file_router


def _cad_client() -> TestClient:
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _file_client() -> TestClient:
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = FastAPI()
    app.include_router(file_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_cad_capabilities_endpoint_returns_consolidated_contract_shape():
    client = _cad_client()
    connectors = [
        SimpleNamespace(
            id="pdf",
            label="PDF",
            cad_format="PDF",
            document_type="2d",
            extensions=["pdf"],
            aliases=[],
            priority=5,
            description="PDF connector",
        ),
        SimpleNamespace(
            id="step",
            label="STEP",
            cad_format="STEP",
            document_type="3d",
            extensions=["step", "stp"],
            aliases=[],
            priority=10,
            description="STEP connector",
        ),
    ]
    settings = SimpleNamespace(
        CAD_CONNECTOR_BASE_URL="http://cad-connector.local",
        CAD_CONNECTOR_MODE="required",
        CAD_CONVERSION_BACKEND_PROFILE="auto",
        CAD_EXTRACTOR_BASE_URL="http://cad-extractor.local",
        CAD_EXTRACTOR_MODE="required",
        CAD_ML_BASE_URL="http://cad-ml.local",
        CADGF_ROUTER_BASE_URL="http://cadgf.local",
    )

    with patch("yuantus.meta_engine.web.cad_router.get_settings", return_value=settings):
        with patch("yuantus.meta_engine.web.cad_router.cad_registry.list", return_value=connectors):
            response = client.get("/api/v1/cad/capabilities")

    assert response.status_code == 200
    body = response.json()

    assert [connector["id"] for connector in body["connectors"]] == ["pdf", "step"]
    assert body["counts"] == {"total": 2, "2d": 1, "3d": 1}
    assert body["formats"] == {"2d": ["PDF"], "3d": ["STEP"]}
    assert body["extensions"] == {"2d": ["pdf"], "3d": ["step", "stp"]}
    assert body["features"]["preview"] == {
        "available": True,
        "modes": ["local", "cad_ml", "connector"],
        "note": None,
        "status": "ok",
        "degraded_reason": None,
    }
    assert body["features"]["bom"] == {
        "available": True,
        "modes": ["connector"],
        "note": "Requires CAD connector service",
        "status": "ok",
        "degraded_reason": None,
    }
    assert body["features"]["manifest"] == {
        "available": True,
        "modes": ["cadgf"],
        "note": "CADGF router produces manifest/document/metadata",
        "status": "ok",
        "degraded_reason": None,
    }
    assert body["features"]["metadata"] == {
        "available": True,
        "modes": ["extract", "cadgf"],
        "note": None,
        "status": "ok",
        "degraded_reason": None,
    }
    assert body["integrations"] == {
        "cad_connector": {
            "configured": True,
            "enabled": True,
            "mode": "required",
            "profile": {
                "configured": "auto",
                "effective": "external-enterprise",
                "source": "legacy-mode",
                "options": [
                    "local-baseline",
                    "hybrid-auto",
                    "external-enterprise",
                ],
            },
            "base_url": "http://cad-connector.local",
            "status": "ok",
            "degraded_reason": None,
        },
        "cad_extractor": {
            "configured": True,
            "mode": "required",
            "base_url": "http://cad-extractor.local",
            "status": "ok",
            "degraded_reason": None,
        },
        "cad_ml": {
            "configured": True,
            "base_url": "http://cad-ml.local",
            "status": "ok",
            "degraded_reason": None,
        },
        "cadgf_router": {
            "configured": True,
            "base_url": "http://cadgf.local",
            "status": "ok",
            "degraded_reason": None,
        },
    }


def test_cad_capabilities_endpoint_disables_connector_backed_modes_when_unconfigured():
    client = _cad_client()
    connectors = [
        SimpleNamespace(
            id="pdf",
            label="PDF",
            cad_format="PDF",
            document_type="2d",
            extensions=["pdf"],
            aliases=[],
            priority=5,
            description=None,
        )
    ]
    settings = SimpleNamespace(
        CAD_CONNECTOR_BASE_URL="",
        CAD_CONNECTOR_MODE="optional",
        CAD_CONVERSION_BACKEND_PROFILE="auto",
        CAD_EXTRACTOR_BASE_URL="",
        CAD_EXTRACTOR_MODE="optional",
        CAD_ML_BASE_URL="",
        CADGF_ROUTER_BASE_URL="",
    )

    with patch("yuantus.meta_engine.web.cad_router.get_settings", return_value=settings):
        with patch("yuantus.meta_engine.web.cad_router.cad_registry.list", return_value=connectors):
            response = client.get("/api/v1/cad/capabilities")

    assert response.status_code == 200
    body = response.json()

    assert body["features"]["preview"]["modes"] == ["local"]
    assert body["features"]["preview"]["status"] == "degraded"
    assert body["features"]["preview"]["degraded_reason"] == "local fallback only"
    assert body["features"]["geometry"]["modes"] == ["local"]
    assert body["features"]["geometry"]["status"] == "degraded"
    assert body["features"]["extract"]["modes"] == ["local"]
    assert body["features"]["extract"]["status"] == "degraded"
    assert body["features"]["bom"] == {
        "available": False,
        "modes": [],
        "note": "Requires CAD connector service",
        "status": "disabled",
        "degraded_reason": "CAD connector service not configured",
    }
    assert body["features"]["metadata"] == {
        "available": True,
        "modes": ["extract"],
        "note": None,
        "status": "degraded",
        "degraded_reason": "local fallback only",
    }
    assert body["integrations"] == {
        "cad_connector": {
            "configured": False,
            "enabled": False,
            "mode": "optional",
            "profile": {
                "configured": "auto",
                "effective": "local-baseline",
                "source": "legacy-mode",
                "options": [
                    "local-baseline",
                    "hybrid-auto",
                    "external-enterprise",
                ],
            },
            "base_url": None,
            "status": "degraded",
            "degraded_reason": "local fallback only",
        },
        "cad_extractor": {
            "configured": False,
            "mode": "optional",
            "base_url": None,
            "status": "degraded",
            "degraded_reason": "local fallback only",
        },
        "cad_ml": {
            "configured": False,
            "base_url": None,
            "status": "degraded",
            "degraded_reason": "local fallback only",
        },
        "cadgf_router": {
            "configured": False,
            "base_url": None,
            "status": "disabled",
            "degraded_reason": "CADGF router not configured",
        },
    }


def test_cad_capabilities_endpoint_reports_explicit_backend_profile_override():
    client = _cad_client()
    settings = SimpleNamespace(
        CAD_CONNECTOR_BASE_URL="http://cad-connector.local",
        CAD_CONNECTOR_MODE="disabled",
        CAD_CONVERSION_BACKEND_PROFILE="hybrid-auto",
        CAD_EXTRACTOR_BASE_URL="",
        CAD_EXTRACTOR_MODE="optional",
        CAD_ML_BASE_URL="",
        CADGF_ROUTER_BASE_URL="",
    )

    with patch("yuantus.meta_engine.web.cad_router.get_settings", return_value=settings):
        with patch("yuantus.meta_engine.web.cad_router.cad_registry.list", return_value=[]):
            response = client.get("/api/v1/cad/capabilities")

    assert response.status_code == 200
    body = response.json()

    assert body["integrations"]["cad_connector"] == {
        "configured": True,
        "enabled": True,
        "mode": "disabled",
        "profile": {
            "configured": "hybrid-auto",
            "effective": "hybrid-auto",
            "source": "profile",
            "options": [
                "local-baseline",
                "hybrid-auto",
                "external-enterprise",
            ],
        },
        "base_url": "http://cad-connector.local",
        "status": "ok",
        "degraded_reason": None,
    }


def test_cad_capabilities_endpoint_honors_scoped_local_override():
    client = _cad_client()
    settings = SimpleNamespace(
        CAD_CONNECTOR_BASE_URL="http://cad-connector.local",
        CAD_CONNECTOR_MODE="required",
        CAD_CONVERSION_BACKEND_PROFILE="external-enterprise",
        CAD_EXTRACTOR_BASE_URL="",
        CAD_EXTRACTOR_MODE="optional",
        CAD_ML_BASE_URL="",
        CADGF_ROUTER_BASE_URL="",
    )

    with patch("yuantus.meta_engine.web.cad_router.get_settings", return_value=settings):
        with patch("yuantus.meta_engine.web.cad_router.cad_registry.list", return_value=[]):
            with patch(
                "yuantus.meta_engine.web.cad_router._resolve_cad_backend_profile_response",
                return_value=CadBackendProfileResolution(
                    configured="local-baseline",
                    effective="local-baseline",
                    source="plugin-config:tenant-org",
                    options=[
                        "local-baseline",
                        "hybrid-auto",
                        "external-enterprise",
                    ],
                    scope={
                        "tenant_id": "tenant-1",
                        "org_id": "org-1",
                        "level": "tenant-org",
                    },
                ),
            ):
                response = client.get("/api/v1/cad/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["features"]["preview"]["modes"] == ["local"]
    assert body["features"]["geometry"]["modes"] == ["local"]
    assert body["features"]["bom"]["available"] is False
    assert body["integrations"]["cad_connector"]["enabled"] is False
    assert body["integrations"]["cad_connector"]["profile"]["source"] == "plugin-config:tenant-org"


def test_supported_formats_endpoint_remains_legacy_but_payload_is_unchanged():
    client = _file_client()

    with patch("yuantus.meta_engine.web.file_router.CADConverterService") as service_cls:
        service_cls.return_value.get_supported_conversions.return_value = {
            "input_formats": ["pdf", "step"],
            "output_formats": ["gltf", "obj"],
            "preview_formats": ["png"],
            "freecad_available": False,
        }
        response = client.get("/api/v1/file/supported-formats")

    assert response.status_code == 200
    assert response.json() == {
        "input_formats": ["pdf", "step"],
        "output_formats": ["gltf", "obj"],
        "preview_formats": ["png"],
        "freecad_available": False,
    }


def test_supported_formats_endpoint_is_marked_deprecated_in_openapi():
    client = _file_client()

    schema = client.get("/openapi.json").json()
    get_operation = schema["paths"]["/api/v1/file/supported-formats"]["get"]

    assert get_operation["deprecated"] is True
