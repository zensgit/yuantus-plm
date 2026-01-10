from __future__ import annotations

import importlib.util
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
