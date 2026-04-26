from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import maintenance_router as maintenance_shim_module


_EXPECTED_MAINTENANCE_ROUTE_OWNERS = {
    ("POST", "/api/v1/maintenance/categories"): "yuantus.meta_engine.web.maintenance_category_router",
    ("GET", "/api/v1/maintenance/categories"): "yuantus.meta_engine.web.maintenance_category_router",
    ("POST", "/api/v1/maintenance/equipment"): "yuantus.meta_engine.web.maintenance_equipment_router",
    ("GET", "/api/v1/maintenance/equipment"): "yuantus.meta_engine.web.maintenance_equipment_router",
    ("GET", "/api/v1/maintenance/equipment/readiness-summary"): "yuantus.meta_engine.web.maintenance_equipment_router",
    ("GET", "/api/v1/maintenance/equipment/{equipment_id}"): "yuantus.meta_engine.web.maintenance_equipment_router",
    ("POST", "/api/v1/maintenance/equipment/{equipment_id}/status"): "yuantus.meta_engine.web.maintenance_equipment_router",
    ("POST", "/api/v1/maintenance/requests"): "yuantus.meta_engine.web.maintenance_request_router",
    ("POST", "/api/v1/maintenance/requests/{request_id}/transition"): "yuantus.meta_engine.web.maintenance_request_router",
    ("GET", "/api/v1/maintenance/requests"): "yuantus.meta_engine.web.maintenance_request_router",
    ("GET", "/api/v1/maintenance/requests/{request_id}"): "yuantus.meta_engine.web.maintenance_request_router",
    ("GET", "/api/v1/maintenance/preventive-schedule"): "yuantus.meta_engine.web.maintenance_schedule_router",
    ("GET", "/api/v1/maintenance/queue-summary"): "yuantus.meta_engine.web.maintenance_schedule_router",
}

_ROUTER_REGISTRATION_ORDER = [
    "maintenance_category_router",
    "maintenance_equipment_router",
    "maintenance_request_router",
    "maintenance_schedule_router",
]


def _is_maintenance_route(path: str) -> bool:
    return path == "/api/v1/maintenance" or path.startswith("/api/v1/maintenance/")


def _app_maintenance_routes() -> dict[tuple[str, str], str]:
    routes: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_maintenance_route(route.path):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            routes[(method, route.path)] = route.endpoint.__module__
    return routes


def test_all_maintenance_routes_have_explicit_split_router_owner() -> None:
    assert _app_maintenance_routes() == _EXPECTED_MAINTENANCE_ROUTE_OWNERS


def test_all_maintenance_routes_are_registered_exactly_once() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_maintenance_route(route.path):
            continue
        for method in route.methods or set():
            if method != "HEAD":
                counts[(method, route.path)] += 1

    assert set(counts) == set(_EXPECTED_MAINTENANCE_ROUTE_OWNERS)
    assert all(count == 1 for count in counts.values())


def test_legacy_maintenance_router_module_is_registered_shell_only() -> None:
    text = Path(maintenance_shim_module.__file__).read_text(encoding="utf-8")
    assert re.findall(r"@maintenance_router\.(get|post|delete|put|patch)\(", text) == []
    assert "maintenance_router = APIRouter" in text


def test_app_registers_maintenance_routers_in_decomposition_order() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    positions = [
        text.find(f"app.include_router({router_name}") for router_name in _ROUTER_REGISTRATION_ORDER
    ]
    assert all(position != -1 for position in positions)
    assert positions == sorted(positions)
    assert "app.include_router(maintenance_router," not in text, (
        "maintenance_router shell must not be registered in app.py after Phase 1 P1.3"
    )


def test_legacy_maintenance_router_owns_no_runtime_paths() -> None:
    leaked = sorted(
        (method, path, owner)
        for (method, path), owner in _app_maintenance_routes().items()
        if owner == "yuantus.meta_engine.web.maintenance_router"
    )
    assert leaked == []
