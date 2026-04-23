from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import eco_impact_apply_router as eco_impact_module
from yuantus.meta_engine.web import eco_router as eco_legacy_module
from yuantus.meta_engine.web.eco_impact_apply_router import eco_impact_apply_router


_MOVED_ROUTE_KEYS = {
    ("GET", "/eco/{eco_id}/impact"),
    ("GET", "/eco/{eco_id}/impact/export"),
    ("GET", "/eco/{eco_id}/bom-diff"),
    ("POST", "/eco/{eco_id}/apply"),
    ("GET", "/eco/{eco_id}/apply-diagnostics"),
}

_EXPECTED_OWNER = "yuantus.meta_engine.web.eco_impact_apply_router"


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


def test_eco_impact_apply_routes_owned_by_split_router() -> None:
    assert _MOVED_ROUTE_KEYS <= _route_keys(eco_impact_apply_router)


def test_create_app_registers_impact_apply_routes_once_with_split_owner() -> None:
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


def test_legacy_eco_router_no_longer_declares_impact_apply_routes() -> None:
    text = Path(eco_legacy_module.__file__).read_text(encoding="utf-8")
    moved_paths = {
        "/{eco_id}/impact",
        "/{eco_id}/impact/export",
        "/{eco_id}/bom-diff",
        "/{eco_id}/apply",
        "/{eco_id}/apply-diagnostics",
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


def test_impact_apply_router_registered_after_workflow_before_legacy_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    workflow_pos = text.find("app.include_router(eco_approval_workflow_router")
    impact_pos = text.find("app.include_router(eco_impact_apply_router")
    legacy_pos = text.find("app.include_router(eco_router")
    assert workflow_pos != -1
    assert impact_pos != -1
    assert legacy_pos != -1
    assert workflow_pos < impact_pos < legacy_pos


def test_impact_apply_routes_preserve_eco_tag() -> None:
    app = create_app()
    expected = {(method, f"/api/v1{path}") for method, path in _MOVED_ROUTE_KEYS}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if (method, route.path) in expected:
                assert "ECO" in (route.tags or [])


def test_impact_apply_router_keeps_lifecycle_and_change_paths_out() -> None:
    text = Path(eco_impact_module.__file__).read_text(encoding="utf-8")
    assert '@eco_impact_apply_router.post("/{eco_id}/cancel")' not in text
    assert '@eco_impact_apply_router.post("/{eco_id}/suspend")' not in text
    assert '@eco_impact_apply_router.post("/{eco_id}/unsuspend")' not in text
    assert '@eco_impact_apply_router.get("/{eco_id}/unsuspend-diagnostics")' not in text
    assert '@eco_impact_apply_router.post("/{eco_id}/move-stage")' not in text
    assert '@eco_impact_apply_router.post("/{eco_id}/compute-changes")' not in text
