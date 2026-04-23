"""Tests for C3 – File / 3D-Viewer contract hardening.

Covers:
  - assess_viewer_readiness() service method
  - GET /{file_id}/viewer_readiness endpoint
  - GET /{file_id}/geometry/assets endpoint
  - viewer_readiness field in FileMetadata response
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.services.cad_converter_service import CADConverterService


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_container(**overrides):
    """Create a mock FileContainer with sensible defaults."""
    defaults = dict(
        id="fc-1",
        filename="model.step",
        file_type="step",
        mime_type="model/step",
        file_size=1024,
        checksum="abc123",
        document_type="3d_model",
        is_native_cad=True,
        cad_format="step",
        cad_connector_id=None,
        author=None,
        source_system=None,
        source_version=None,
        document_version=None,
        system_path="/vault/fc-1/model.step",
        geometry_path=None,
        cad_manifest_path=None,
        preview_path=None,
        preview_data=None,
        cad_document_path=None,
        cad_metadata_path=None,
        cad_bom_path=None,
        cad_dedup_path=None,
        cad_document_schema_version=None,
        cad_review_state=None,
        cad_review_note=None,
        cad_review_by_id=None,
        cad_reviewed_at=None,
        conversion_status=None,
        created_at=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _client_with_file_container(fc):
    """Return a TestClient whose DB mock returns *fc* on db.get(FileContainer, ...)."""
    mock_db = MagicMock()
    mock_db.get.return_value = fc

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def override_user():
        return 42

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_user
    return TestClient(app), mock_db


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestAssessViewerReadiness:

    def test_full_mode_when_geometry_and_manifest(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_manifest_path="/vault/fc-1/manifest.json",
        )
        service = CADConverterService(MagicMock())
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            result = service.assess_viewer_readiness(fc)

        assert result["viewer_mode"] == "full"
        assert result["geometry_available"] is True
        assert result["manifest_available"] is True
        assert result["is_viewer_ready"] is True
        assert result["geometry_format"] == "obj"

    def test_geometry_only_mode(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.glb")
        service = CADConverterService(MagicMock())
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            result = service.assess_viewer_readiness(fc)

        assert result["viewer_mode"] == "geometry_only"
        assert result["geometry_format"] == "glb"
        assert result["is_viewer_ready"] is True

    def test_manifest_only_mode(self):
        fc = _make_file_container(cad_manifest_path="/vault/fc-1/manifest.json")
        service = CADConverterService(MagicMock())
        result = service.assess_viewer_readiness(fc)

        assert result["viewer_mode"] == "manifest_only"
        assert result["geometry_available"] is False
        assert result["is_viewer_ready"] is True

    def test_preview_only_mode(self):
        fc = _make_file_container(preview_path="/vault/fc-1/preview.png")
        service = CADConverterService(MagicMock())
        result = service.assess_viewer_readiness(fc)

        assert result["viewer_mode"] == "preview_only"
        assert result["preview_available"] is True
        assert result["is_viewer_ready"] is False

    def test_none_mode_when_no_assets(self):
        fc = _make_file_container()
        service = CADConverterService(MagicMock())
        result = service.assess_viewer_readiness(fc)

        assert result["viewer_mode"] == "none"
        assert result["is_viewer_ready"] is False

    def test_blocking_reason_conversion_pending(self):
        fc = _make_file_container(is_native_cad=True, conversion_status="pending")
        service = CADConverterService(MagicMock())
        result = service.assess_viewer_readiness(fc)

        assert "conversion_pending" in result["blocking_reasons"]
        assert result["is_viewer_ready"] is False

    def test_blocking_reason_conversion_failed(self):
        fc = _make_file_container(is_native_cad=True, conversion_status="failed")
        service = CADConverterService(MagicMock())
        result = service.assess_viewer_readiness(fc)

        assert "conversion_failed" in result["blocking_reasons"]

    def test_no_blocking_reason_for_non_native_cad(self):
        fc = _make_file_container(is_native_cad=False, conversion_status="pending")
        service = CADConverterService(MagicMock())
        result = service.assess_viewer_readiness(fc)

        assert result["blocking_reasons"] == []

    def test_sidecar_detection(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.gltf")
        service = CADConverterService(MagicMock())
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            def exists_side_effect(path):
                return path.endswith(".bin")

            MockFS.return_value.file_exists.side_effect = exists_side_effect
            result = service.assess_viewer_readiness(fc)

        assert "model.gltf" in result["available_assets"]
        assert "model.bin" in result["available_assets"]
        assert len(result["available_assets"]) == 2

    def test_schema_version_passthrough(self):
        fc = _make_file_container(
            cad_manifest_path="/vault/fc-1/manifest.json",
            cad_document_schema_version=3,
        )
        service = CADConverterService(MagicMock())
        result = service.assess_viewer_readiness(fc)

        assert result["schema_version"] == 3


# ---------------------------------------------------------------------------
# Router-level tests
# ---------------------------------------------------------------------------


class TestViewerReadinessEndpoint:

    def test_viewer_readiness_endpoint_returns_assessment(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_manifest_path="/vault/fc-1/manifest.json",
        )
        client, _db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.get("/api/v1/file/fc-1/viewer_readiness")

        assert resp.status_code == 200
        body = resp.json()
        assert body["viewer_mode"] == "full"
        assert body["is_viewer_ready"] is True

    def test_viewer_readiness_404_for_missing_file(self):
        client, mock_db = _client_with_file_container(None)
        mock_db.get.return_value = None
        resp = client.get("/api/v1/file/missing/viewer_readiness")
        assert resp.status_code == 404


class TestGeometryAssetsEndpoint:

    def test_asset_catalog_returns_list(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.gltf")
        client, _db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.get("/api/v1/file/fc-1/geometry/assets")

        assert resp.status_code == 200
        body = resp.json()
        assert body["file_id"] == "fc-1"
        assert body["geometry_format"] == "gltf"
        assert "model.gltf" in body["assets"]
        assert body["total"] >= 1

    def test_asset_catalog_empty_when_no_geometry(self):
        fc = _make_file_container()
        client, _db = _client_with_file_container(fc)
        resp = client.get("/api/v1/file/fc-1/geometry/assets")
        assert resp.status_code == 200
        body = resp.json()
        assert body["assets"] == []
        assert body["total"] == 0

    def test_asset_catalog_404_for_missing_file(self):
        client, mock_db = _client_with_file_container(None)
        mock_db.get.return_value = None
        resp = client.get("/api/v1/file/missing/geometry/assets")
        assert resp.status_code == 404


class TestFileMetadataViewerReadinessField:

    def test_file_metadata_includes_viewer_readiness(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_manifest_path="/vault/fc-1/manifest.json",
        )
        client, _db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.get("/api/v1/file/fc-1")

        assert resp.status_code == 200
        body = resp.json()
        vr = body.get("viewer_readiness")
        assert vr is not None
        assert vr["viewer_mode"] == "full"
        assert vr["is_viewer_ready"] is True


# ---------------------------------------------------------------------------
# C11 – Consumer Readiness Endpoints
# ---------------------------------------------------------------------------


class TestConsumerSummaryEndpoint:

    def test_consumer_summary_full_mode(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_manifest_path="/vault/fc-1/manifest.json",
            cad_review_by_id=7,
            cad_review_state="approved",
            cad_review_note="ready",
            cad_reviewed_at=datetime(2026, 3, 19, 12, 0, 0),
        )
        client, _db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.get("/api/v1/file/fc-1/consumer-summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["file_id"] == "fc-1"
        assert body["viewer_mode"] == "full"
        assert body["is_viewer_ready"] is True
        assert body["urls"]["geometry"] is not None
        assert body["urls"]["manifest"] is not None
        assert body["urls"]["download"] is not None
        assert "proof" in body
        assert body["proof"]["review"]["state"] == "approved"
        assert body["proof"]["review"]["reviewed_by"] == {"id": 7}
        assert body["proof"]["review"]["reviewed_at"] == "2026-03-19T12:00:00"
        assert body["proof"]["audit"]["enabled"] is False

    def test_consumer_summary_none_mode(self):
        fc = _make_file_container()
        client, _db = _client_with_file_container(fc)
        resp = client.get("/api/v1/file/fc-1/consumer-summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["viewer_mode"] == "none"
        assert body["is_viewer_ready"] is False
        assert body["urls"]["geometry"] is None
        assert "proof" in body

    def test_consumer_summary_404(self):
        client, mock_db = _client_with_file_container(None)
        mock_db.get.return_value = None
        resp = client.get("/api/v1/file/missing/consumer-summary")
        assert resp.status_code == 404

    def test_consumer_summary_with_audit(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_review_by_id=7,
            cad_review_state="approved",
            cad_reviewed_at=datetime(2026, 3, 19, 12, 0, 0),
        )
        client, mock_db = _client_with_file_container(fc)
        log_item = SimpleNamespace(
            id="log-1",
            action="cad_review_update",
            created_at=datetime(2026, 3, 19, 12, 0, 1),
            user_id=7,
            payload={"note": "approved"},
        )
        (
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
        ).all.return_value = [log_item]
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.get(
                "/api/v1/file/fc-1/consumer-summary"
                "?include_audit=true&include_reviewer_profile=true"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["proof"]["audit"]["enabled"] is True
        assert body["proof"]["audit"]["history_count"] == 1
        assert body["proof"]["audit"]["history"][0]["action"] == "cad_review_update"
        assert body["proof"]["audit"]["history"][0]["id"] == "log-1"

    def test_consumer_summary_with_audit_history_limit(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_review_by_id=7,
            cad_review_state="approved",
            cad_reviewed_at=datetime(2026, 3, 19, 12, 0, 0),
        )
        client, mock_db = _client_with_file_container(fc)
        (
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
        ).all.return_value = [
            SimpleNamespace(
                id="log-1",
                action="cad_review_update",
                created_at=datetime(2026, 3, 19, 12, 0, 1),
                user_id=7,
                payload={"note": "approved"},
            ),
        ]
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.get(
                "/api/v1/file/fc-1/consumer-summary?include_audit=true&history_limit=1"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["proof"]["audit"]["enabled"] is True
        assert body["proof"]["audit"]["history_count"] == 1
        assert body["proof"]["audit"]["history"][0]["id"] == "log-1"


class TestViewerReadinessExport:

    def test_export_json_format(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
        )
        client, mock_db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.post(
                "/api/v1/file/viewer-readiness/export",
                json={"file_ids": ["fc-1"]},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["ready_count"] == 1
        assert body["not_found_count"] == 0
        assert body["requested_file_count"] == 1
        assert "generated_at" in body
        assert body["files"][0]["viewer_mode"] == "geometry_only"

    def test_export_csv_format_case_insensitive(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.obj")
        client, mock_db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.post(
                "/api/v1/file/viewer-readiness/export?export_format=CSV",
                json={"file_ids": ["fc-1"]},
            )

        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.content.decode("utf-8")
        assert "file_id" in content
        assert "fc-1" in content

    def test_export_missing_file_included(self):
        client, mock_db = _client_with_file_container(None)
        mock_db.get.return_value = None
        resp = client.post(
            "/api/v1/file/viewer-readiness/export",
            json={"file_ids": ["no-such"]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["not_ready_count"] == 1
        assert body["not_found_count"] == 1
        assert body["files"][0]["viewer_mode"] == "not_found"

    def test_export_csv_format(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.obj")
        client, mock_db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.post(
                "/api/v1/file/viewer-readiness/export?export_format=csv",
                json={"file_ids": ["fc-1"]},
            )

        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        content = resp.content.decode("utf-8")
        assert "file_id" in content
        assert "fc-1" in content

    def test_export_empty_file_ids_400(self):
        client, _ = _client_with_file_container(None)
        resp = client.post(
            "/api/v1/file/viewer-readiness/export",
            json={"file_ids": []},
        )
        assert resp.status_code == 400

    def test_export_invalid_payload_type(self):
        client, _ = _client_with_file_container(None)
        resp = client.post(
            "/api/v1/file/viewer-readiness/export",
            json={"file_ids": "fc-1"},
        )
        assert resp.status_code == 422

    def test_export_invalid_export_format(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.obj")
        client, _ = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.post(
                "/api/v1/file/viewer-readiness/export?export_format=xml",
                json={"file_ids": ["fc-1"]},
            )

        assert resp.status_code == 400

    def test_export_invalid_batch_size_400(self):
        client, _ = _client_with_file_container(None)
        resp = client.post(
            "/api/v1/file/viewer-readiness/export",
            json={"file_ids": ["x"] * 201},
        )
        assert resp.status_code == 400

    def test_export_invalid_history_limit(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.obj")
        client, _ = _client_with_file_container(fc)
        resp = client.post(
            "/api/v1/file/viewer-readiness/export?include_audit=true&history_limit=0",
            json={"file_ids": ["fc-1"]},
        )
        assert resp.status_code == 422

    def test_export_csv_with_audit_columns(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_review_by_id=8,
            cad_review_state="approved",
        )
        client, mock_db = _client_with_file_container(fc)
        log_item = SimpleNamespace(
            id="log-1",
            action="cad_review_update",
            created_at=datetime(2026, 3, 19, 12, 0, 1),
            user_id=8,
            payload={"note": "approved"},
        )
        (
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
        ).all.return_value = [log_item]
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.post(
                "/api/v1/file/viewer-readiness/export?export_format=csv&include_audit=true",
                json={"file_ids": ["fc-1"]},
            )

        assert resp.status_code == 200
        assert "history_count" in resp.text
        assert "history_latest_action" in resp.text
        assert "cad_review_update" in resp.text


class TestGeometryPackSummary:

    def test_pack_summary_single_file(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.glb",
        )
        client, mock_db = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.post(
                "/api/v1/file/geometry-pack-summary",
                json={"file_ids": ["fc-1"]},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_files"] == 1
        assert body["files_found"] == 1
        assert body["viewer_ready_count"] == 1
        assert body["format_counts"]["glb"] == 1
        assert body["pack"][0]["file_id"] == "fc-1"
        assert "proof" in body["pack"][0]

    def test_pack_summary_missing_file(self):
        client, mock_db = _client_with_file_container(None)
        mock_db.get.return_value = None
        resp = client.post(
            "/api/v1/file/geometry-pack-summary",
            json={"file_ids": ["no-such"]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_files"] == 1
        assert body["files_found"] == 0
        assert body["not_found_count"] == 1
        assert body["pack"][0]["found"] is False
        assert body["audited_files"] == 0

    def test_pack_summary_empty_400(self):
        client, _ = _client_with_file_container(None)
        resp = client.post(
            "/api/v1/file/geometry-pack-summary",
            json={"file_ids": []},
        )
        assert resp.status_code == 400

    def test_pack_summary_with_audit_and_no_assets(self):
        fc = _make_file_container(
            geometry_path="/vault/fc-1/model.obj",
            cad_review_by_id=9,
            cad_review_state="approved",
        )
        client, mock_db = _client_with_file_container(fc)
        (
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
        ).all.return_value = []
        resp = client.post(
            "/api/v1/file/geometry-pack-summary?include_audit=true&include_assets=false",
            json={"file_ids": ["fc-1"]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["audited_files"] == 1
        assert body["pack"][0]["proof"]["audit"]["enabled"] is True
        assert body["pack"][0]["assets"] == []

    def test_pack_summary_assets_toggle(self):
        fc = _make_file_container(geometry_path="/vault/fc-1/model.obj")
        client, _ = _client_with_file_container(fc)
        with patch(
            "yuantus.meta_engine.services.file_service.FileService"
        ) as MockFS:
            MockFS.return_value.file_exists.return_value = False
            resp = client.post(
                "/api/v1/file/geometry-pack-summary?include_assets=false",
                json={"file_ids": ["fc-1"]},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["pack"][0]["assets"] == []
