"""
Focused regression for CAD handler binding wrappers.
"""

import pytest
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.tasks.cad_pipeline_tasks import (
    _enrich_with_derived_files,
    cad_preview_with_binding,
    cad_geometry_with_binding,
)


class TestEnrichWithDerivedFiles:
    def test_adds_derived_files_on_success(self):
        result = {"ok": True, "file_id": "fc-1", "preview_path": "/p.png"}
        payload = {"version_id": "ver-1"}
        enriched = _enrich_with_derived_files(result, payload, "preview")
        assert enriched["derived_files"] == [
            {"file_id": "fc-1", "file_role": "preview", "version_id": "ver-1"}
        ]

    def test_skips_on_failure(self):
        result = {"ok": False, "file_id": "fc-1", "error": "boom"}
        payload = {"version_id": "ver-1"}
        enriched = _enrich_with_derived_files(result, payload, "preview")
        assert "derived_files" not in enriched

    def test_skips_when_no_version_id(self):
        result = {"ok": True, "file_id": "fc-1"}
        payload = {"file_id": "fc-1"}
        enriched = _enrich_with_derived_files(result, payload, "preview")
        assert "derived_files" not in enriched


class TestBindingWrappers:
    @patch("yuantus.meta_engine.tasks.cad_pipeline_tasks.cad_preview")
    def test_preview_wrapper_enriches_success(self, mock_preview):
        mock_preview.return_value = {
            "ok": True,
            "file_id": "fc-99",
            "preview_path": "previews/fc/fc-99.png",
        }
        result = cad_preview_with_binding(
            {"file_id": "fc-99", "version_id": "ver-A"}, MagicMock()
        )
        assert result["derived_files"] == [
            {"file_id": "fc-99", "file_role": "preview", "version_id": "ver-A"}
        ]

    @patch("yuantus.meta_engine.tasks.cad_pipeline_tasks.cad_geometry")
    def test_geometry_wrapper_enriches_success(self, mock_geometry):
        mock_geometry.return_value = {
            "ok": True,
            "file_id": "fc-50",
            "geometry_path": "geometry/fc/fc-50.gltf",
        }
        result = cad_geometry_with_binding(
            {"file_id": "fc-50", "version_id": "ver-G"}, MagicMock()
        )
        assert result["derived_files"] == [
            {"file_id": "fc-50", "file_role": "geometry", "version_id": "ver-G"}
        ]

    def test_cli_registers_binding_wrappers(self):
        from pathlib import Path

        cli_path = Path(__file__).resolve().parents[3] / "yuantus" / "cli.py"
        source = cli_path.read_text()
        assert "cad_preview_with_binding" in source
        assert "cad_geometry_with_binding" in source
