from __future__ import annotations

from collections import Counter

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web.parallel_tasks_cad_3d_router import (
    parallel_tasks_cad_3d_router,
)
from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router


_CAD_3D_ROUTE_KEYS = {
    ("POST", "/cad-3d/overlays"),
    ("GET", "/cad-3d/overlays/cache/stats"),
    ("GET", "/cad-3d/overlays/{document_item_id}"),
    ("POST", "/cad-3d/overlays/{document_item_id}/components/resolve-batch"),
    ("GET", "/cad-3d/overlays/{document_item_id}/components/{component_ref}"),
    # G3 3D visual explode (validated explode-config persistence).
    ("PUT", "/cad-3d/explode/{document_item_id}"),
    ("GET", "/cad-3d/explode/{document_item_id}"),
    # G3 BOM auto-layout R1 (default explode config from the BOM tree).
    ("POST", "/cad-3d/explode/{document_item_id}/auto-layout"),
}


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


def test_cad_3d_routes_owned_by_split_router():
    assert _CAD_3D_ROUTE_KEYS <= _route_keys(parallel_tasks_cad_3d_router)


def test_parallel_tasks_router_no_longer_owns_cad_3d_routes():
    assert not {
        path
        for _method, path in _route_keys(parallel_tasks_router)
        if path.startswith("/cad-3d")
    }


def test_cache_stats_route_precedes_dynamic_overlay_lookup_route():
    paths = [
        route.path
        for route in parallel_tasks_cad_3d_router.routes
        if isinstance(route, APIRoute)
    ]
    assert paths.index("/cad-3d/overlays/cache/stats") < paths.index(
        "/cad-3d/overlays/{document_item_id}"
    )


def test_create_app_registers_cad_3d_routes_once():
    app = create_app()
    counts: Counter[tuple[str, str]] = Counter()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1/cad-3d"):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            counts[(method, route.path)] += 1

    expected = {(method, f"/api/v1{path}") for method, path in _CAD_3D_ROUTE_KEYS}
    assert set(counts) == expected
    assert all(count == 1 for count in counts.values())


# --------------------------------------------------------------------------
# G3 BOM auto-layout R1 — §8 static guards (taskbook #684): source-scan the
# auto-layout code for the forbidden assumptions, not behavior.
# --------------------------------------------------------------------------


def _auto_layout_code_only() -> str:
    """Source of the auto-layout functions with docstrings + line comments
    stripped — so a guard scans the CODE, not prose that legitimately *names*
    the forbidden concepts (e.g. the docstring documenting the §4 LOCK)."""
    import inspect
    import re

    from yuantus.meta_engine.services.parallel_tasks_service import ThreeDOverlayService

    src = "\n".join(
        inspect.getsource(fn)
        for fn in (
            ThreeDOverlayService.build_auto_layout,
            ThreeDOverlayService._flatten_bom_nodes,
            ThreeDOverlayService._auto_layout_offset,
        )
    )
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    return "\n".join(line.split("#", 1)[0] for line in src.splitlines())


def test_auto_layout_does_no_server_side_geometry():
    low = _auto_layout_code_only().lower()
    for forbidden in ("trimesh", "bounding_box", "bbox", "centroid", "vertices", "mesh"):
        assert forbidden not in low, (
            f"auto-layout code must stay geometry-free; found {forbidden!r}"
        )


def test_auto_layout_never_equates_component_ref_to_item_id():
    code = _auto_layout_code_only()
    stripped = code.replace(" ", "")
    for forbidden in ("component_ref==item_id", "item_id==component_ref"):
        assert forbidden not in stripped, (
            "auto-layout must NOT assume component_ref == item_id (taskbook §4 LOCK)"
        )
    # positive: the explicit relationship_id/item_id binding machinery is present.
    assert "relationship_id" in code and "item_id_counts" in code


def test_auto_layout_adds_no_table_or_migration():
    code = _auto_layout_code_only()
    for forbidden in ("__tablename__", "op.create_table", "Column("):
        assert forbidden not in code, f"auto-layout must add no table/model: {forbidden}"


def test_auto_layout_has_no_odoo_or_gpl_reference():
    low = _auto_layout_code_only().lower()
    for forbidden in ("odoo", "gpl", "agpl"):
        assert forbidden not in low, f"no GPL/AGPL/OdooPLM reuse: {forbidden}"
