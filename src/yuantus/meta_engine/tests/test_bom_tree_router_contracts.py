"""
Route ownership contracts for BOM Router Decomposition R2: Tree / Effective / Version / Convert.

These contracts pin the mechanical relocation of 5 public /api/v1/bom endpoints
(/{item_id}/effective, /version/{version_id}, /convert/ebom-to-mbom,
/{parent_id}/tree, /mbom/{parent_id}/tree) from bom_router.py to
bom_tree_router.py. They protect against accidental regressions that would
silently move a tree/effective/version/convert route back to bom_router,
or break 3-way registration order (compare -> tree -> legacy) /
path uniqueness / tag / source declaration order.

Mirrors the cadence used by BOM R1 and the CAD R1-R12 decomposition contracts.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from yuantus.api.app import create_app
from yuantus.meta_engine.web import bom_tree_router as bom_tree_module
from yuantus.meta_engine.web import bom_router as bom_legacy_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/bom/{item_id}/effective"),
    ("GET", "/api/v1/bom/version/{version_id}"),
    ("POST", "/api/v1/bom/convert/ebom-to-mbom"),
    ("GET", "/api/v1/bom/{parent_id}/tree"),
    ("GET", "/api/v1/bom/mbom/{parent_id}/tree"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.bom_tree_router"


def _collect_app_routes(app):
    """Return a list of (methods_set, path, endpoint.__module__) for APIRoute entries."""
    from fastapi.routing import APIRoute

    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_bom_tree_router() -> None:
    """Every one of the 5 moved routes must resolve to bom_tree_router."""
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

    moved_literals = {
        "/{item_id}/effective",
        "/version/{version_id}",
        "/convert/ebom-to-mbom",
        "/{parent_id}/tree",
        "/mbom/{parent_id}/tree",
    }

    pattern = re.compile(r'@bom_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = []
    for method, path in pattern.findall(text):
        if path in moved_literals:
            leaked.append((method.upper(), path))

    assert not leaked, (
        f"bom_router.py still declares tree/effective/version/convert route handlers: {leaked}. "
        f"They must live in bom_tree_router.py."
    )


def test_bom_tree_router_is_registered_between_compare_and_legacy() -> None:
    """app.py must register the three BOM routers in order:
    bom_compare_router -> bom_tree_router -> bom_router.

    This preserves deterministic route resolution order after R2. Even though
    the 5 R2 paths do not currently collide with compare or legacy paths,
    keeping a canonical ordering makes future slice-by-slice splits safe to
    review mechanically.
    """
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")

    compare_pos = text.find("app.include_router(bom_compare_router")
    tree_pos = text.find("app.include_router(bom_tree_router")
    legacy_pos = text.find("app.include_router(bom_router")
    assert compare_pos != -1, "bom_compare_router is not registered in app.py"
    assert tree_pos != -1, "bom_tree_router is not registered in app.py"
    assert legacy_pos != -1, "bom_router is not registered in app.py"
    assert compare_pos < tree_pos < legacy_pos, (
        "Registration order must be bom_compare_router -> bom_tree_router -> "
        f"bom_router; got compare={compare_pos}, tree={tree_pos}, legacy={legacy_pos}."
    )


def test_each_moved_path_is_registered_exactly_once() -> None:
    """FastAPI app must have exactly one route per (method, path) pair for the 5 entries."""
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


def test_source_declaration_order_effective_version_convert_tree_mbom_tree() -> None:
    """Declaration order in bom_tree_router.py must be
    /{item_id}/effective -> /version/{version_id} -> /convert/ebom-to-mbom ->
    /{parent_id}/tree -> /mbom/{parent_id}/tree.

    This is a mechanical relocation guard -- the 5 paths do NOT collide with
    each other by shape, so source-order here is not required for FastAPI
    routing correctness. But pinning the order lets reviewers mechanically
    diff the relocation against the pre-split bom_router.py and catch any
    silent handler-body change.
    """
    source_path = Path(bom_tree_module.__file__)
    text = source_path.read_text(encoding="utf-8")

    effective_idx = text.find('"/{item_id}/effective"')
    version_idx = text.find('"/version/{version_id}"')
    convert_idx = text.find('"/convert/ebom-to-mbom"')
    tree_idx = text.find('"/{parent_id}/tree"')
    mbom_tree_idx = text.find('"/mbom/{parent_id}/tree"')

    assert effective_idx != -1, "/{item_id}/effective literal not found"
    assert version_idx != -1, "/version/{version_id} literal not found"
    assert convert_idx != -1, "/convert/ebom-to-mbom literal not found"
    assert tree_idx != -1, "/{parent_id}/tree literal not found"
    assert mbom_tree_idx != -1, "/mbom/{parent_id}/tree literal not found"

    assert effective_idx < version_idx < convert_idx < tree_idx < mbom_tree_idx, (
        "Declaration order in bom_tree_router.py must be "
        "effective -> version -> convert -> tree -> mbom tree "
        f"(got effective={effective_idx}, version={version_idx}, "
        f"convert={convert_idx}, tree={tree_idx}, mbom_tree={mbom_tree_idx})."
    )
