"""
Route ownership contracts for BOM Router Decomposition R1: Compare.

These contracts pin the mechanical relocation of 14 /api/v1/bom/compare*
endpoints from bom_router.py to bom_compare_router.py. They protect against
accidental regressions that would silently move a compare route back to
bom_router or break registration order / path uniqueness.

Mirrors the cadence used by the CAD R1-R12 decomposition contracts.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from yuantus.api.app import create_app
from yuantus.meta_engine.web import bom_compare_router as bom_compare_module
from yuantus.meta_engine.web import bom_router as bom_legacy_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/bom/compare/schema"),
    ("GET", "/api/v1/bom/compare"),
    ("GET", "/api/v1/bom/compare/delta/preview"),
    ("GET", "/api/v1/bom/compare/delta/export"),
    ("GET", "/api/v1/bom/compare/summarized"),
    ("GET", "/api/v1/bom/compare/summarized/export"),
    ("POST", "/api/v1/bom/compare/summarized/snapshots"),
    ("GET", "/api/v1/bom/compare/summarized/snapshots/compare"),
    ("GET", "/api/v1/bom/compare/summarized/snapshots/compare/export"),
    ("GET", "/api/v1/bom/compare/summarized/snapshots/{snapshot_id}/compare/current"),
    ("GET", "/api/v1/bom/compare/summarized/snapshots/{snapshot_id}/compare/current/export"),
    ("GET", "/api/v1/bom/compare/summarized/snapshots/{snapshot_id}/export"),
    ("GET", "/api/v1/bom/compare/summarized/snapshots/{snapshot_id}"),
    ("GET", "/api/v1/bom/compare/summarized/snapshots"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.bom_compare_router"


def _collect_app_routes(app):
    """Return a list of (methods_set, path, endpoint.__module__) for APIRoute entries."""
    from fastapi.routing import APIRoute

    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_bom_compare_router() -> None:
    """Every one of the 14 moved routes must resolve to bom_compare_router."""
    app = create_app()
    entries = _collect_app_routes(app)

    resolved: dict[tuple[str, str], str] = {}
    for methods, path, module in entries:
        for m in methods:
            key = (m, path)
            if key in MOVED_ROUTES:
                resolved[key] = module

    missing = sorted(MOVED_ROUTES - set(resolved.keys()))
    assert not missing, f"Expected moved routes not registered: {missing}"

    wrong_owner = sorted(
        (m, p, mod) for (m, p), mod in resolved.items() if mod != EXPECTED_OWNER_MODULE
    )
    assert not wrong_owner, (
        f"Expected {EXPECTED_OWNER_MODULE} to own these; found other owners: {wrong_owner}"
    )


def test_moved_routes_are_absent_from_legacy_bom_router() -> None:
    """bom_router.py must not declare @bom_router.(get|post) for any moved path."""
    source_path = Path(bom_legacy_module.__file__)
    text = source_path.read_text(encoding="utf-8")

    compare_paths = {
        "/compare/schema",
        "/compare",
        "/compare/delta/preview",
        "/compare/delta/export",
        "/compare/summarized",
        "/compare/summarized/export",
        "/compare/summarized/snapshots",
        "/compare/summarized/snapshots/compare",
        "/compare/summarized/snapshots/compare/export",
        "/compare/summarized/snapshots/{snapshot_id}",
        "/compare/summarized/snapshots/{snapshot_id}/export",
        "/compare/summarized/snapshots/{snapshot_id}/compare/current",
        "/compare/summarized/snapshots/{snapshot_id}/compare/current/export",
    }

    pattern = re.compile(r'@bom_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = []
    for method, path in pattern.findall(text):
        if path in compare_paths or path.startswith("/compare"):
            leaked.append((method.upper(), path))

    assert not leaked, (
        f"bom_router.py still declares compare route handlers: {leaked}. "
        f"They must live in bom_compare_router.py."
    )


def test_bom_compare_router_is_registered_before_legacy_bom_router() -> None:
    """app.py must register bom_compare_router before bom_router so the
    static /snapshots/compare route is resolved before any dynamic
    /{snapshot_id} pattern and owner resolution is stable."""
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")

    compare_pos = text.find("app.include_router(bom_compare_router")
    legacy_pos = text.find("app.include_router(bom_router")
    assert compare_pos != -1, "bom_compare_router is not registered in app.py"
    assert legacy_pos != -1, "bom_router is not registered in app.py"
    assert compare_pos < legacy_pos, (
        "bom_compare_router must be registered BEFORE bom_router to preserve "
        "deterministic route resolution order after R1."
    )


def test_each_moved_path_is_registered_exactly_once() -> None:
    """FastAPI app must have exactly one route per (method, path) pair for the 14 entries."""
    app = create_app()
    entries = _collect_app_routes(app)

    counts: dict[tuple[str, str], int] = {}
    for methods, path, _module in entries:
        for m in methods:
            key = (m, path)
            if key in MOVED_ROUTES:
                counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(k for k, c in counts.items() if c > 1)
    missing = sorted(MOVED_ROUTES - set(counts.keys()))
    assert not duplicates, f"Duplicate registrations for: {duplicates}"
    assert not missing, f"Missing route registrations: {missing}"


def test_moved_routes_preserve_bom_tag() -> None:
    """Source handlers used tags=['BOM']; the new router must expose the same tag."""
    app = create_app()
    from fastapi.routing import APIRoute

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for m in route.methods or []:
            key = (m, route.path)
            if key in MOVED_ROUTES:
                assert "BOM" in (route.tags or []), (
                    f"Route {m} {route.path} lost its BOM tag after move "
                    f"(tags={route.tags})."
                )


def test_static_snapshot_compare_route_precedes_dynamic_snapshot_route() -> None:
    """Declaration order in bom_compare_router.py must have
    /snapshots/compare (static) before /snapshots/{snapshot_id} (dynamic)
    so FastAPI does not capture 'compare' as a snapshot_id."""
    source_path = Path(bom_compare_module.__file__)
    text = source_path.read_text(encoding="utf-8")

    # Index of literal path strings in source order.
    compare_idx = text.find('"/compare/summarized/snapshots/compare"')
    dynamic_idx = text.find('"/compare/summarized/snapshots/{snapshot_id}"')
    assert compare_idx != -1, "/snapshots/compare static route literal not found"
    assert dynamic_idx != -1, "/snapshots/{snapshot_id} dynamic route literal not found"
    assert compare_idx < dynamic_idx, (
        "Static /snapshots/compare must be declared before dynamic "
        "/snapshots/{snapshot_id} in bom_compare_router.py; otherwise "
        "FastAPI may capture 'compare' as a snapshot_id value."
    )
