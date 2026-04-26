from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import subcontracting_router as subcontracting_shim_module


_EXPECTED_SUBCONTRACTING_ROUTE_OWNERS = {
    ("POST", "/api/v1/subcontracting/orders"): "yuantus.meta_engine.web.subcontracting_orders_router",
    ("GET", "/api/v1/subcontracting/orders"): "yuantus.meta_engine.web.subcontracting_orders_router",
    ("GET", "/api/v1/subcontracting/orders/{order_id}"): "yuantus.meta_engine.web.subcontracting_orders_router",
    ("POST", "/api/v1/subcontracting/orders/{order_id}/assign-vendor"): "yuantus.meta_engine.web.subcontracting_orders_router",
    ("POST", "/api/v1/subcontracting/orders/{order_id}/issue-material"): "yuantus.meta_engine.web.subcontracting_orders_router",
    ("POST", "/api/v1/subcontracting/orders/{order_id}/record-receipt"): "yuantus.meta_engine.web.subcontracting_orders_router",
    ("GET", "/api/v1/subcontracting/orders/{order_id}/timeline"): "yuantus.meta_engine.web.subcontracting_orders_router",
    ("GET", "/api/v1/subcontracting/overview"): "yuantus.meta_engine.web.subcontracting_analytics_router",
    ("GET", "/api/v1/subcontracting/vendors/analytics"): "yuantus.meta_engine.web.subcontracting_analytics_router",
    ("GET", "/api/v1/subcontracting/receipts/analytics"): "yuantus.meta_engine.web.subcontracting_analytics_router",
    ("GET", "/api/v1/subcontracting/export/overview"): "yuantus.meta_engine.web.subcontracting_analytics_router",
    ("GET", "/api/v1/subcontracting/export/vendors"): "yuantus.meta_engine.web.subcontracting_analytics_router",
    ("GET", "/api/v1/subcontracting/export/receipts"): "yuantus.meta_engine.web.subcontracting_analytics_router",
    ("POST", "/api/v1/subcontracting/approval-role-mappings"): "yuantus.meta_engine.web.subcontracting_approval_mapping_router",
    ("GET", "/api/v1/subcontracting/approval-role-mappings"): "yuantus.meta_engine.web.subcontracting_approval_mapping_router",
    ("GET", "/api/v1/subcontracting/approval-role-mappings/export"): "yuantus.meta_engine.web.subcontracting_approval_mapping_router",
}

_ROUTER_REGISTRATION_ORDER = [
    "subcontracting_orders_router",
    "subcontracting_analytics_router",
    "subcontracting_approval_mapping_router",
]


def _is_subcontracting_route(path: str) -> bool:
    return path == "/api/v1/subcontracting" or path.startswith("/api/v1/subcontracting/")


def _app_subcontracting_routes() -> dict[tuple[str, str], str]:
    routes: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_subcontracting_route(route.path):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            routes[(method, route.path)] = route.endpoint.__module__
    return routes


def test_all_subcontracting_routes_have_explicit_split_router_owner() -> None:
    assert _app_subcontracting_routes() == _EXPECTED_SUBCONTRACTING_ROUTE_OWNERS


def test_all_subcontracting_routes_are_registered_exactly_once() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_subcontracting_route(route.path):
            continue
        for method in route.methods or set():
            if method != "HEAD":
                counts[(method, route.path)] += 1

    assert set(counts) == set(_EXPECTED_SUBCONTRACTING_ROUTE_OWNERS)
    assert all(count == 1 for count in counts.values())


def test_legacy_subcontracting_router_module_is_registered_shell_only() -> None:
    text = Path(subcontracting_shim_module.__file__).read_text(encoding="utf-8")
    assert re.findall(r"@subcontracting_router\.(get|post|delete|put|patch)\(", text) == []
    assert "subcontracting_router = APIRouter" in text


def test_app_registers_subcontracting_routers_in_decomposition_order() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    positions = [
        text.find(f"app.include_router({router_name}") for router_name in _ROUTER_REGISTRATION_ORDER
    ]
    assert all(position != -1 for position in positions)
    assert positions == sorted(positions)
    assert "app.include_router(subcontracting_router," not in text, (
        "subcontracting_router shell must not be registered in app.py after Phase 1 P1.4"
    )


def test_legacy_subcontracting_router_owns_no_runtime_paths() -> None:
    leaked = sorted(
        (method, path, owner)
        for (method, path), owner in _app_subcontracting_routes().items()
        if owner == "yuantus.meta_engine.web.subcontracting_router"
    )
    assert leaked == []
