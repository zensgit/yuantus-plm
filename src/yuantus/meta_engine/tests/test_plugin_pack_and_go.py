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
    path = module._build_package_path("Part/001", "native_cad", "../file.step")
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
