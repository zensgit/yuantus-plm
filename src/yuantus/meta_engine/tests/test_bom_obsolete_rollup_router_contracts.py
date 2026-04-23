"""
Route ownership contracts for BOM Router Decomposition R4: Obsolete + Rollup.

These contracts pin the mechanical relocation of 3 public /api/v1/bom endpoints
(GET /{item_id}/obsolete, POST /{item_id}/obsolete/resolve, and
POST /{item_id}/rollup/weight) from bom_router.py to
bom_obsolete_rollup_router.py. They protect route ownership, legacy absence,
canonical registration order, duplicate registration, tag preservation, and
source declaration order.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from yuantus.api.app import create_app
from yuantus.meta_engine.web import bom_obsolete_rollup_router as bom_obsolete_rollup_module
from yuantus.meta_engine.web import bom_router as bom_legacy_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/bom/{item_id}/obsolete"),
    ("POST", "/api/v1/bom/{item_id}/obsolete/resolve"),
    ("POST", "/api/v1/bom/{item_id}/rollup/weight"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.bom_obsolete_rollup_router"


def _collect_app_routes(app):
    """Return a list of (methods_set, path, endpoint.__module__) for APIRoute entries."""
    from fastapi.routing import APIRoute

    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_bom_obsolete_rollup_router() -> None:
    """All R4 moved routes must resolve to bom_obsolete_rollup_router."""
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
    """bom_router.py must not declare @bom_router for obsolete/rollup paths."""
    source_path = Path(bom_legacy_module.__file__)
    text = source_path.read_text(encoding="utf-8")

    moved_literals = {
        "/{item_id}/obsolete",
        "/{item_id}/obsolete/resolve",
        "/{item_id}/rollup/weight",
    }

    pattern = re.compile(r'@bom_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = []
    for method, path in pattern.findall(text):
        if path in moved_literals:
            leaked.append((method.upper(), path))

    assert not leaked, (
        f"bom_router.py still declares obsolete/rollup route handlers: {leaked}. "
        f"They must live in bom_obsolete_rollup_router.py."
    )


def test_bom_obsolete_rollup_router_is_registered_before_legacy() -> None:
    """app.py must register BOM routers in canonical decomposition order."""
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")

    compare_pos = text.find("app.include_router(bom_compare_router")
    tree_pos = text.find("app.include_router(bom_tree_router")
    children_pos = text.find("app.include_router(bom_children_router")
    obsolete_rollup_pos = text.find("app.include_router(bom_obsolete_rollup_router")
    legacy_pos = text.find("app.include_router(bom_router")
    assert compare_pos != -1, "bom_compare_router is not registered in app.py"
    assert tree_pos != -1, "bom_tree_router is not registered in app.py"
    assert children_pos != -1, "bom_children_router is not registered in app.py"
    assert obsolete_rollup_pos != -1, "bom_obsolete_rollup_router is not registered in app.py"
    assert legacy_pos != -1, "bom_router is not registered in app.py"
    assert compare_pos < tree_pos < children_pos < obsolete_rollup_pos < legacy_pos, (
        "Registration order must be bom_compare_router -> bom_tree_router -> "
        "bom_children_router -> bom_obsolete_rollup_router -> bom_router; got "
        f"compare={compare_pos}, tree={tree_pos}, children={children_pos}, "
        f"obsolete_rollup={obsolete_rollup_pos}, legacy={legacy_pos}."
    )


def test_each_moved_path_is_registered_exactly_once() -> None:
    """FastAPI app must have exactly one route per (method, path) pair for R4 paths."""
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


def test_source_declaration_order_obsolete_resolve_rollup() -> None:
    """Declaration order in bom_obsolete_rollup_router.py must be obsolete -> resolve -> rollup."""
    source_path = Path(bom_obsolete_rollup_module.__file__)
    text = source_path.read_text(encoding="utf-8")

    obsolete_idx = text.find('"/{item_id}/obsolete"')
    resolve_idx = text.find('"/{item_id}/obsolete/resolve"')
    rollup_idx = text.find('"/{item_id}/rollup/weight"')
    assert obsolete_idx != -1, "/{item_id}/obsolete literal not found"
    assert resolve_idx != -1, "/{item_id}/obsolete/resolve literal not found"
    assert rollup_idx != -1, "/{item_id}/rollup/weight literal not found"
    assert obsolete_idx < resolve_idx < rollup_idx, (
        "Declaration order in bom_obsolete_rollup_router.py must be "
        f"obsolete -> resolve -> rollup (got obsolete={obsolete_idx}, "
        f"resolve={resolve_idx}, rollup={rollup_idx})."
    )
