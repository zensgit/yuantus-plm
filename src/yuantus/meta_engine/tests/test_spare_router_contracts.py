"""Route ownership contracts for the G5 spare-parts router (OdooPLM gap parity).

DB-off / pure introspection (no DB, no fixture). Pins the spare router's HTTP
surface so a future refactor breaks loudly here. spare_router is a NEW router
(not a relocation), so these contracts assert presence, ownership, single
registration, tag, source declaration order, and registration order relative to
its sibling equivalent_router — mirroring
``test_bom_substitutes_router_contracts.py``.

Companion taskbook: ``docs/DEVELOPMENT_ODOOPLM_G5_SPARE_PARTS_TASKBOOK_20260529.md``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Set, Tuple

from yuantus.api.app import create_app
from yuantus.meta_engine.web import spare_router as spare_module


SPARE_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/items/{item_id}/spares"),
    ("POST", "/api/v1/items/{item_id}/spares"),
    ("DELETE", "/api/v1/items/{item_id}/spares/{spare_id}"),
    ("GET", "/api/v1/items/{item_id}/spares/explode"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.spare_router"


def _collect_app_routes(app):
    """Return (methods_set, path, endpoint.__module__) for APIRoute entries."""
    from fastapi.routing import APIRoute

    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append(
                (frozenset(route.methods or []), route.path, route.endpoint.__module__)
            )
    return entries


def test_spare_routes_are_owned_by_spare_router() -> None:
    app = create_app()
    entries = _collect_app_routes(app)

    resolved: dict[tuple[str, str], str] = {}
    for methods, path, module in entries:
        for m in methods:
            key = (m, path)
            if key in SPARE_ROUTES:
                resolved[key] = module

    missing = sorted(SPARE_ROUTES - set(resolved.keys()))
    assert not missing, f"Expected spare routes not registered: {missing}"

    wrong_owner = sorted(
        (m, p, mod) for (m, p), mod in resolved.items() if mod != EXPECTED_OWNER_MODULE
    )
    assert not wrong_owner, (
        f"Expected {EXPECTED_OWNER_MODULE} to own these; found other owners: {wrong_owner}"
    )


def test_each_spare_path_is_registered_exactly_once() -> None:
    app = create_app()
    entries = _collect_app_routes(app)

    counts: dict[tuple[str, str], int] = {}
    for methods, path, _module in entries:
        for m in methods:
            key = (m, path)
            if key in SPARE_ROUTES:
                counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(k for k, c in counts.items() if c > 1)
    missing = sorted(SPARE_ROUTES - set(counts.keys()))
    assert not duplicates, f"Duplicate registrations for: {duplicates}"
    assert not missing, f"Missing route registrations: {missing}"


def test_spare_routes_carry_item_spares_tag() -> None:
    app = create_app()
    from fastapi.routing import APIRoute

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for m in route.methods or []:
            key = (m, route.path)
            if key in SPARE_ROUTES:
                assert "Item Spares" in (route.tags or []), (
                    f"Route {m} {route.path} lost its 'Item Spares' tag "
                    f"(tags={route.tags})."
                )


def test_source_declaration_order_list_add_remove_explode() -> None:
    """Declaration order in spare_router.py: list -> add -> remove -> explode."""
    text = Path(spare_module.__file__).read_text(encoding="utf-8")

    list_idx = text.find('@spare_router.get(\n    "/{item_id}/spares"')
    add_idx = text.find('@spare_router.post(\n    "/{item_id}/spares"')
    remove_idx = text.find('"/{item_id}/spares/{spare_id}"')
    explode_idx = text.find('"/{item_id}/spares/explode"')
    assert list_idx != -1, "GET /{item_id}/spares decorator not found"
    assert add_idx != -1, "POST /{item_id}/spares decorator not found"
    assert remove_idx != -1, "DELETE /{item_id}/spares/{spare_id} literal not found"
    assert explode_idx != -1, "GET /{item_id}/spares/explode literal not found"
    assert list_idx < add_idx < remove_idx < explode_idx, (
        "Declaration order in spare_router.py must be list -> add -> remove -> "
        f"explode (got list={list_idx}, add={add_idx}, remove={remove_idx}, "
        f"explode={explode_idx})."
    )


def test_spare_router_registered_after_equivalent_router() -> None:
    """app.py must register spare_router (after equivalent_router) exactly once."""
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")

    equivalent_pos = text.find("app.include_router(equivalent_router")
    spare_pos = text.find("app.include_router(spare_router")
    assert equivalent_pos != -1, "equivalent_router is not registered in app.py"
    assert spare_pos != -1, "spare_router is not registered in app.py"
    assert equivalent_pos < spare_pos, (
        "spare_router must be registered after equivalent_router "
        f"(got equivalent={equivalent_pos}, spare={spare_pos})."
    )
    assert text.count("app.include_router(spare_router") == 1, (
        "spare_router must be registered exactly once."
    )
