from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import eco_lifecycle_router as eco_lifecycle_module
from yuantus.meta_engine.web import eco_router as eco_legacy_module
from yuantus.meta_engine.web.eco_lifecycle_router import eco_lifecycle_router


_MOVED_ROUTE_KEYS = {
    ("POST", "/eco/{eco_id}/cancel"),
    ("GET", "/eco/{eco_id}/unsuspend-diagnostics"),
    ("POST", "/eco/{eco_id}/suspend"),
    ("POST", "/eco/{eco_id}/unsuspend"),
    ("POST", "/eco/{eco_id}/move-stage"),
}

_EXPECTED_OWNER = "yuantus.meta_engine.web.eco_lifecycle_router"


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


def test_eco_lifecycle_routes_owned_by_split_router() -> None:
    assert _MOVED_ROUTE_KEYS <= _route_keys(eco_lifecycle_router)


def test_create_app_registers_lifecycle_routes_once_with_split_owner() -> None:
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


def test_legacy_eco_router_no_longer_declares_lifecycle_routes() -> None:
    text = Path(eco_legacy_module.__file__).read_text(encoding="utf-8")
    moved_paths = {
        "/{eco_id}/cancel",
        "/{eco_id}/unsuspend-diagnostics",
        "/{eco_id}/suspend",
        "/{eco_id}/unsuspend",
        "/{eco_id}/move-stage",
    }
    pattern = re.compile(
        r'@eco_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"',
        re.DOTALL,
    )
    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(text)
        if path in moved_paths
    ]
    assert leaked == []


def test_lifecycle_router_registered_after_change_analysis_before_legacy_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    change_pos = text.find("app.include_router(eco_change_analysis_router")
    lifecycle_pos = text.find("app.include_router(eco_lifecycle_router")
    core_pos = text.find("app.include_router(eco_core_router")
    assert change_pos != -1
    assert lifecycle_pos != -1
    assert core_pos != -1
    assert change_pos < lifecycle_pos < core_pos


def test_lifecycle_routes_preserve_eco_tag() -> None:
    app = create_app()
    expected = {(method, f"/api/v1{path}") for method, path in _MOVED_ROUTE_KEYS}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if (method, route.path) in expected:
                assert "ECO" in (route.tags or [])


def test_lifecycle_router_keeps_crud_impact_and_change_paths_out() -> None:
    text = Path(eco_lifecycle_module.__file__).read_text(encoding="utf-8")
    assert '@eco_lifecycle_router.post("")' not in text
    assert '@eco_lifecycle_router.get("")' not in text
    assert '@eco_lifecycle_router.get("/{eco_id}")' not in text
    assert '@eco_lifecycle_router.post("/{eco_id}/bind-product")' not in text
    assert '@eco_lifecycle_router.post("/{eco_id}/new-revision")' not in text
    assert '@eco_lifecycle_router.get("/{eco_id}/impact")' not in text
    assert '@eco_lifecycle_router.post("/{eco_id}/compute-changes")' not in text
