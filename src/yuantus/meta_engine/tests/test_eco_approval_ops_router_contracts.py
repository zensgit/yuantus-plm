from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import eco_approval_ops_router as eco_ops_module
from yuantus.meta_engine.web import eco_router as eco_legacy_module
from yuantus.meta_engine.web.eco_approval_ops_router import eco_approval_ops_router


_MOVED_ROUTE_KEYS = {
    ("GET", "/eco/approvals/dashboard/summary"),
    ("GET", "/eco/approvals/dashboard/items"),
    ("GET", "/eco/approvals/dashboard/export"),
    ("GET", "/eco/approvals/audit/anomalies"),
}

_EXPECTED_OWNER = "yuantus.meta_engine.web.eco_approval_ops_router"


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


def test_eco_approval_ops_routes_owned_by_split_router() -> None:
    assert _MOVED_ROUTE_KEYS <= _route_keys(eco_approval_ops_router)


def test_create_app_registers_eco_approval_ops_routes_once_with_split_owner() -> None:
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


def test_legacy_eco_router_no_longer_declares_approval_ops_routes() -> None:
    text = Path(eco_legacy_module.__file__).read_text(encoding="utf-8")
    moved_paths = {
        "/approvals/dashboard/summary",
        "/approvals/dashboard/items",
        "/approvals/dashboard/export",
        "/approvals/audit/anomalies",
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


def test_eco_approval_ops_router_registered_before_legacy_eco_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    ops_pos = text.find("app.include_router(eco_approval_ops_router")
    core_pos = text.find("app.include_router(eco_core_router")
    assert ops_pos != -1
    assert core_pos != -1
    assert ops_pos < core_pos


def test_eco_approval_ops_routes_preserve_eco_tag() -> None:
    app = create_app()
    expected = {(method, f"/api/v1{path}") for method, path in _MOVED_ROUTE_KEYS}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if (method, route.path) in expected:
                assert "ECO" in (route.tags or [])


def test_eco_approval_ops_router_keeps_write_paths_out() -> None:
    text = Path(eco_ops_module.__file__).read_text(encoding="utf-8")
    assert '@eco_approval_ops_router.post("/{eco_id}/auto-assign-approvers")' not in text
    assert '@eco_approval_ops_router.post("/approvals/escalate-overdue")' not in text
    assert '@eco_approval_ops_router.post("/{eco_id}/approve")' not in text
    assert '@eco_approval_ops_router.post("/{eco_id}/reject")' not in text
    assert '@eco_approval_ops_router.get("/{eco_id}/approvals")' not in text
