from __future__ import annotations

import re
from pathlib import Path

from yuantus.meta_engine.web import file_router as file_legacy_module


def test_legacy_file_router_shell_declares_no_runtime_routes() -> None:
    text = Path(file_legacy_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(
        r'@file_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"',
        re.DOTALL,
    )
    assert pattern.findall(text) == []


def test_legacy_file_router_shell_is_not_registered_in_app() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    assert "from yuantus.meta_engine.web.file_router import file_router" not in text
    assert "app.include_router(file_router" not in text


def test_all_file_split_routers_registered_in_expected_order() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    positions = [
        text.find("app.include_router(file_conversion_router"),
        text.find("app.include_router(file_viewer_router"),
        text.find("app.include_router(file_storage_router"),
        text.find("app.include_router(file_attachment_router"),
        text.find("app.include_router(file_metadata_router"),
    ]
    assert all(pos != -1 for pos in positions)
    assert positions == sorted(positions)
