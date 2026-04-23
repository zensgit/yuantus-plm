from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import file_router as file_shim_module


_EXPECTED_FILE_ROUTE_OWNERS = {
    ("GET", "/api/v1/file/supported-formats"): "yuantus.meta_engine.web.file_conversion_router",
    ("GET", "/api/v1/file/{file_id}/conversion_summary"): "yuantus.meta_engine.web.file_conversion_router",
    ("POST", "/api/v1/file/{file_id}/convert"): "yuantus.meta_engine.web.file_conversion_router",
    ("GET", "/api/v1/file/conversion/{job_id}"): "yuantus.meta_engine.web.file_conversion_router",
    ("GET", "/api/v1/file/conversions/pending"): "yuantus.meta_engine.web.file_conversion_router",
    ("POST", "/api/v1/file/conversions/process"): "yuantus.meta_engine.web.file_conversion_router",
    ("POST", "/api/v1/file/process_cad"): "yuantus.meta_engine.web.file_conversion_router",
    ("GET", "/api/v1/file/{file_id}/viewer_readiness"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/geometry/assets"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/consumer-summary"): "yuantus.meta_engine.web.file_viewer_router",
    ("POST", "/api/v1/file/viewer-readiness/export"): "yuantus.meta_engine.web.file_viewer_router",
    ("POST", "/api/v1/file/geometry-pack-summary"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/geometry"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/asset/{asset_name}"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/cad_asset/{asset_name}"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/cad_manifest"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/cad_document"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/cad_metadata"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/cad_bom"): "yuantus.meta_engine.web.file_viewer_router",
    ("GET", "/api/v1/file/{file_id}/cad_dedup"): "yuantus.meta_engine.web.file_viewer_router",
    ("POST", "/api/v1/file/upload"): "yuantus.meta_engine.web.file_storage_router",
    ("GET", "/api/v1/file/{file_id}/download"): "yuantus.meta_engine.web.file_storage_router",
    ("GET", "/api/v1/file/{file_id}/preview"): "yuantus.meta_engine.web.file_storage_router",
    ("POST", "/api/v1/file/attach"): "yuantus.meta_engine.web.file_attachment_router",
    ("GET", "/api/v1/file/item/{item_id}"): "yuantus.meta_engine.web.file_attachment_router",
    ("DELETE", "/api/v1/file/attachment/{attachment_id}"): "yuantus.meta_engine.web.file_attachment_router",
    ("GET", "/api/v1/file/{file_id}"): "yuantus.meta_engine.web.file_metadata_router",
}

_ROUTER_REGISTRATION_ORDER = [
    "file_conversion_router",
    "file_viewer_router",
    "file_storage_router",
    "file_attachment_router",
    "file_metadata_router",
]


def _is_file_route(path: str) -> bool:
    return path == "/api/v1/file" or path.startswith("/api/v1/file/")


def _app_file_routes() -> dict[tuple[str, str], str]:
    routes: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_file_route(route.path):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            routes[(method, route.path)] = route.endpoint.__module__
    return routes


def test_all_file_routes_have_explicit_split_router_owner() -> None:
    assert _app_file_routes() == _EXPECTED_FILE_ROUTE_OWNERS


def test_all_file_routes_are_registered_exactly_once() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_file_route(route.path):
            continue
        for method in route.methods or set():
            if method != "HEAD":
                counts[(method, route.path)] += 1

    assert set(counts) == set(_EXPECTED_FILE_ROUTE_OWNERS)
    assert all(count == 1 for count in counts.values())


def test_legacy_file_router_module_is_unregistered_shell_only() -> None:
    text = Path(file_shim_module.__file__).read_text(encoding="utf-8")
    assert re.findall(r"@file_router\.(get|post|delete|put|patch)\(", text) == []
    assert "file_router = APIRouter" in text


def test_app_registers_file_routers_in_decomposition_order_without_legacy_shell() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    positions = [
        text.find(f"app.include_router({router_name}")
        for router_name in _ROUTER_REGISTRATION_ORDER
    ]

    assert all(position != -1 for position in positions)
    assert positions == sorted(positions)
    assert "from yuantus.meta_engine.web.file_router import file_router" not in text
    assert "app.include_router(file_router" not in text
