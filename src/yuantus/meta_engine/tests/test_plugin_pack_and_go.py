from __future__ import annotations

import csv
import importlib.util
import io
import sys
from pathlib import Path


def _load_plugin_module():
    root = Path(__file__).resolve().parents[4]
    plugin_path = root / "plugins" / "yuantus-pack-and-go" / "main.py"
    spec = importlib.util.spec_from_file_location("pack_and_go_plugin", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_file_roles_adds_flags():
    module = _load_plugin_module()
    roles = module._normalize_file_roles(
        ["native_cad"],
        include_previews=True,
        include_printouts=True,
        include_geometry=False,
    )
    assert "native_cad" in roles
    assert "preview" in roles
    assert "printout" in roles
    assert "geometry" not in roles


def test_build_package_path_sanitizes_components():
    module = _load_plugin_module()
    path = module._build_package_path(
        "Part/001",
        "native_cad",
        "../file.step",
        path_strategy="item_role",
        document_type="3d",
    )
    assert ".." not in path
    assert path.endswith("native_cad/file.step")


def test_safe_filename_strips_paths():
    module = _load_plugin_module()
    assert module._safe_filename("../bom.json", "bom_tree.json") == "bom.json"


def test_build_manifest_csv_includes_columns():
    module = _load_plugin_module()
    entries = [
        {
            "file_id": "file-1",
            "filename": "part.step",
            "output_filename": "P-1_A.step",
            "file_role": "native_cad",
            "document_type": "3d",
            "cad_format": "STEP",
            "size": 12,
            "path_in_package": "P-1/native_cad/part.step",
            "source_item_id": "item-1",
            "source_item_number": "P-1",
        }
    ]
    payload = module._build_manifest_csv(entries)
    rows = list(csv.reader(io.StringIO(payload)))
    assert rows[0] == list(module._MANIFEST_CSV_COLUMNS)
    assert rows[1][0] == "file-1"


def test_normalize_export_type_accepts_aliases():
    module = _load_plugin_module()
    assert module._normalize_export_type("2d+pdf") == "2dpdf"
    assert module._normalize_export_type("3d-2d") == "3d2d"


def test_resolve_export_preset_pdf_defaults():
    module = _load_plugin_module()
    file_roles, document_types, include_printouts, include_geometry, normalized = (
        module._resolve_export_preset(
            export_type="pdf",
            file_roles=None,
            document_types=None,
            include_printouts=True,
            include_geometry=True,
            fields_set=set(),
        )
    )
    assert normalized == "pdf"
    assert file_roles == ["printout"]
    assert include_printouts is True
    assert include_geometry is False


def test_normalize_filename_mode_accepts_aliases():
    module = _load_plugin_module()
    assert module._normalize_filename_mode("item_number+rev") == "item_number_rev"
    assert module._normalize_filename_mode("internal-ref") == "internal_ref"


def test_normalize_path_strategy_accepts_aliases():
    module = _load_plugin_module()
    assert module._normalize_path_strategy("item-role") == "item_role"
    assert module._normalize_path_strategy("doc-type") == "document_type"


def test_build_output_filename_item_number_rev():
    module = _load_plugin_module()
    filename = module._build_output_filename(
        "part.step",
        filename_mode="item_number_rev",
        item_number="P-100",
        internal_ref=None,
        revision="A",
    )
    assert filename == "P-100_A.step"


def test_ensure_unique_path_appends_suffix():
    module = _load_plugin_module()
    used = {"P-1/native_cad/part.step"}
    path = module._ensure_unique_path(
        "P-1/native_cad/part.step", file_id="abcdef123456", used_paths=used
    )
    assert path != "P-1/native_cad/part.step"
    assert "abcdef12" in path


def test_ensure_unique_path_increments_counter():
    module = _load_plugin_module()
    used = {
        "P-1/native_cad/part.step",
        "P-1/native_cad/part_abcdef12.step",
    }
    path = module._ensure_unique_path(
        "P-1/native_cad/part.step", file_id="abcdef123456", used_paths=used
    )
    assert path.endswith("_1.step")
