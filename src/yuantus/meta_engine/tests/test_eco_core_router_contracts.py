from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import eco_core_router as eco_core_module
from yuantus.meta_engine.web import eco_router as eco_shim_module
from yuantus.meta_engine.web.eco_core_router import eco_core_router


_CORE_ROUTE_KEYS = {
    ("GET", "/eco/kanban"),
    ("POST", "/eco"),
    ("GET", "/eco"),
    ("GET", "/eco/{eco_id}"),
    ("POST", "/eco/{eco_id}/bind-product"),
    ("PUT", "/eco/{eco_id}"),
    ("DELETE", "/eco/{eco_id}"),
    ("POST", "/eco/{eco_id}/new-revision"),
}

_EXPECTED_OWNER = "yuantus.meta_engine.web.eco_core_router"


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


def test_core_routes_owned_by_core_router() -> None:
    assert _CORE_ROUTE_KEYS <= _route_keys(eco_core_router)


def test_create_app_registers_core_routes_once_with_core_owner() -> None:
    app = create_app()
    expected = {(method, f"/api/v1{path}") for method, path in _CORE_ROUTE_KEYS}
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


def test_eco_router_shim_no_longer_declares_route_decorators() -> None:
    text = Path(eco_shim_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(r"@eco_router\.(get|post|delete|put|patch)\(")
    assert pattern.findall(text) == []


def test_core_router_registered_after_lifecycle_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    lifecycle_pos = text.find("app.include_router(eco_lifecycle_router")
    core_pos = text.find("app.include_router(eco_core_router")
    assert lifecycle_pos != -1
    assert core_pos != -1
    assert lifecycle_pos < core_pos


def test_core_routes_preserve_eco_tag() -> None:
    app = create_app()
    expected = {(method, f"/api/v1{path}") for method, path in _CORE_ROUTE_KEYS}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if (method, route.path) in expected:
                assert "ECO" in (route.tags or [])


def test_core_router_keeps_split_paths_out() -> None:
    text = Path(eco_core_module.__file__).read_text(encoding="utf-8")
    assert '@eco_core_router.get("/approvals/dashboard/summary")' not in text
    assert '@eco_core_router.get("/stages")' not in text
    assert '@eco_core_router.post("/{eco_id}/approve")' not in text
    assert '@eco_core_router.get("/{eco_id}/impact")' not in text
    assert '@eco_core_router.post("/{eco_id}/compute-changes")' not in text
    assert '@eco_core_router.post("/{eco_id}/cancel")' not in text
    assert '@eco_core_router.post("/{eco_id}/move-stage")' not in text


def test_core_router_static_kanban_declared_before_dynamic_eco_id() -> None:
    text = Path(eco_core_module.__file__).read_text(encoding="utf-8")
    kanban_pos = text.find('@eco_core_router.get("/kanban"')
    get_by_id_pos = text.find('@eco_core_router.get("/{eco_id}"')
    assert kanban_pos != -1
    assert get_by_id_pos != -1
    assert kanban_pos < get_by_id_pos
