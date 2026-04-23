from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import file_metadata_router as file_metadata_module
from yuantus.meta_engine.web import file_router as file_legacy_module
from yuantus.meta_engine.web.file_metadata_router import file_metadata_router


_MOVED_ROUTE_KEYS = {
    ("GET", "/file/{file_id}"),
}

_EXPECTED_OWNER = "yuantus.meta_engine.web.file_metadata_router"


def _route_keys(router, *, prefix: str = "") -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            keys.add((method, f"{prefix}{route.path}"))
    return keys


def test_file_metadata_route_owned_by_split_router() -> None:
    assert _MOVED_ROUTE_KEYS <= _route_keys(file_metadata_router)


def test_create_app_registers_file_metadata_route_once_with_split_owner() -> None:
    app = create_app()
    expected = {(method, f"/api/v1{path}") for method, path in _MOVED_ROUTE_KEYS}
    counts: Counter[tuple[str, str]] = Counter()
    wrong_owner: list[tuple[str, str, str]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            key = (method, route.path)
            if key not in expected:
                continue
            counts[key] += 1
            if route.endpoint.__module__ != _EXPECTED_OWNER:
                wrong_owner.append((method, route.path, route.endpoint.__module__))

    assert set(counts) == expected
    assert all(count == 1 for count in counts.values())
    assert wrong_owner == []


def test_legacy_file_router_no_longer_declares_metadata_route() -> None:
    text = Path(file_legacy_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(
        r'@file_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"',
        re.DOTALL,
    )
    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(text)
        if path == "/{file_id}"
    ]
    assert leaked == []


def test_file_metadata_router_registered_after_attachment_before_legacy() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    attachment_pos = text.find("app.include_router(file_attachment_router")
    metadata_pos = text.find("app.include_router(file_metadata_router")
    legacy_pos = text.find("app.include_router(file_router")
    assert attachment_pos != -1
    assert metadata_pos != -1
    assert legacy_pos != -1
    assert attachment_pos < metadata_pos < legacy_pos


def test_file_metadata_route_preserves_file_management_tag() -> None:
    app = create_app()
    expected = {(method, f"/api/v1{path}") for method, path in _MOVED_ROUTE_KEYS}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if (method, route.path) in expected:
                assert "File Management" in (route.tags or [])


def test_file_metadata_router_keeps_storage_and_attachment_out() -> None:
    text = Path(file_metadata_module.__file__).read_text(encoding="utf-8")
    assert '@file_metadata_router.post("/upload")' not in text
    assert '@file_metadata_router.get("/{file_id}/download")' not in text
    assert '@file_metadata_router.get("/{file_id}/preview")' not in text
    assert '@file_metadata_router.post("/attach")' not in text
    assert '@file_metadata_router.get("/item/{item_id}")' not in text
    assert '@file_metadata_router.delete("/attachment/{attachment_id}")' not in text
