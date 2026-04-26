"""
Route ownership contracts for BOM Router Decomposition R5: Where-Used.

These contracts pin the mechanical relocation of 2 public /api/v1/bom endpoints
(GET /{item_id}/where-used and GET /where-used/schema) from bom_router.py to
bom_where_used_router.py. They protect route ownership, legacy absence,
canonical registration order, duplicate registration, tag preservation, and
source declaration order.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from yuantus.api.app import create_app
from yuantus.meta_engine.web import bom_router as bom_legacy_module
from yuantus.meta_engine.web import bom_where_used_router as bom_where_used_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/bom/{item_id}/where-used"),
    ("GET", "/api/v1/bom/where-used/schema"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.bom_where_used_router"


def _collect_app_routes(app):
    """Return a list of (methods_set, path, endpoint.__module__) for APIRoute entries."""
    from fastapi.routing import APIRoute

    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_bom_where_used_router() -> None:
    """Both R5 moved routes must resolve to bom_where_used_router."""
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
    """bom_router.py must not declare @bom_router for where-used paths."""
    source_path = Path(bom_legacy_module.__file__)
    text = source_path.read_text(encoding="utf-8")

    moved_literals = {
        "/{item_id}/where-used",
        "/where-used/schema",
    }

    pattern = re.compile(r'@bom_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = []
    for method, path in pattern.findall(text):
        if path in moved_literals:
            leaked.append((method.upper(), path))

    assert not leaked, (
        f"bom_router.py still declares where-used route handlers: {leaked}. "
        f"They must live in bom_where_used_router.py."
    )


def test_bom_where_used_router_is_registered_after_obsolete_rollup_router() -> None:
    """app.py must register BOM routers in canonical decomposition order;
    legacy bom_router shell must be absent."""
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")

    compare_pos = text.find("app.include_router(bom_compare_router")
    tree_pos = text.find("app.include_router(bom_tree_router")
    children_pos = text.find("app.include_router(bom_children_router")
    obsolete_rollup_pos = text.find("app.include_router(bom_obsolete_rollup_router")
    where_used_pos = text.find("app.include_router(bom_where_used_router")
    assert compare_pos != -1, "bom_compare_router is not registered in app.py"
    assert tree_pos != -1, "bom_tree_router is not registered in app.py"
    assert children_pos != -1, "bom_children_router is not registered in app.py"
    assert obsolete_rollup_pos != -1, "bom_obsolete_rollup_router is not registered in app.py"
    assert where_used_pos != -1, "bom_where_used_router is not registered in app.py"
    assert compare_pos < tree_pos < children_pos < obsolete_rollup_pos < where_used_pos, (
        "Registration order must be bom_compare_router -> bom_tree_router -> "
        "bom_children_router -> bom_obsolete_rollup_router -> bom_where_used_router; "
        f"got compare={compare_pos}, tree={tree_pos}, children={children_pos}, "
        f"obsolete_rollup={obsolete_rollup_pos}, where_used={where_used_pos}."
    )
    assert "app.include_router(bom_router," not in text, (
        "Legacy bom_router shell must not be registered after Phase 1 P1.8"
    )


def test_each_moved_path_is_registered_exactly_once() -> None:
    """FastAPI app must have exactly one route per (method, path) pair for R5 paths."""
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


def test_source_declaration_order_where_used_before_schema() -> None:
    """Declaration order in bom_where_used_router.py must preserve the legacy order."""
    source_path = Path(bom_where_used_module.__file__)
    text = source_path.read_text(encoding="utf-8")

    where_used_idx = text.find('"/{item_id}/where-used"')
    schema_idx = text.find('"/where-used/schema"')
    assert where_used_idx != -1, "/{item_id}/where-used literal not found"
    assert schema_idx != -1, "/where-used/schema literal not found"
    assert where_used_idx < schema_idx, (
        "Declaration order in bom_where_used_router.py must be where-used -> schema "
        f"(got where_used={where_used_idx}, schema={schema_idx})."
    )
