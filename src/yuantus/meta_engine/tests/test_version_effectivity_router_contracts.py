from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import version_router as legacy_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("POST", "/api/v1/versions/{version_id}/effectivity"),
    ("GET", "/api/v1/versions/items/{item_id}/effective"),
    ("GET", "/api/v1/versions/items/{item_id}/tree"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.version_effectivity_router"


def _collect_app_routes(app):
    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_version_effectivity_router() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for methods, path, module in _collect_app_routes(create_app()):
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                resolved[key] = module

    missing = sorted(MOVED_ROUTES - set(resolved))
    wrong_owner = sorted(
        (method, path, module)
        for (method, path), module in resolved.items()
        if module != EXPECTED_OWNER_MODULE
    )
    assert missing == []
    assert wrong_owner == []


def test_moved_routes_are_absent_from_legacy_version_router() -> None:
    text = Path(legacy_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(
        r'@version_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"',
        re.DOTALL,
    )
    moved_paths = {
        "/{version_id}/effectivity",
        "/items/{item_id}/effective",
        "/items/{item_id}/tree",
    }
    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(text)
        if path in moved_paths
    ]
    assert leaked == []


def test_version_effectivity_router_registered_before_legacy_version_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    split_pos = text.find("app.include_router(version_effectivity_router")
    legacy_pos = text.find("app.include_router(version_router")
    assert split_pos != -1
    assert legacy_pos != -1
    assert split_pos < legacy_pos


def test_each_moved_path_is_registered_exactly_once() -> None:
    counts: dict[tuple[str, str], int] = {}
    for methods, path, _module in _collect_app_routes(create_app()):
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(key for key, count in counts.items() if count > 1)
    missing = sorted(MOVED_ROUTES - set(counts))
    assert duplicates == []
    assert missing == []


def test_moved_routes_preserve_versioning_tag() -> None:
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in MOVED_ROUTES:
                assert "Versioning" in (route.tags or [])
