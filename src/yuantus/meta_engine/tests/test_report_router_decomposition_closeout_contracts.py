from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import report_router as report_shim_module


_EXPECTED_REPORT_ROUTE_OWNERS = {
    ("POST", "/api/v1/reports/saved-searches"): "yuantus.meta_engine.web.report_saved_search_router",
    ("GET", "/api/v1/reports/saved-searches"): "yuantus.meta_engine.web.report_saved_search_router",
    ("GET", "/api/v1/reports/saved-searches/{saved_search_id}"): "yuantus.meta_engine.web.report_saved_search_router",
    ("PATCH", "/api/v1/reports/saved-searches/{saved_search_id}"): "yuantus.meta_engine.web.report_saved_search_router",
    ("DELETE", "/api/v1/reports/saved-searches/{saved_search_id}"): "yuantus.meta_engine.web.report_saved_search_router",
    ("POST", "/api/v1/reports/saved-searches/{saved_search_id}/run"): "yuantus.meta_engine.web.report_saved_search_router",
    ("GET", "/api/v1/reports/summary"): "yuantus.meta_engine.web.report_summary_search_router",
    ("POST", "/api/v1/reports/search"): "yuantus.meta_engine.web.report_summary_search_router",
    ("POST", "/api/v1/reports/definitions"): "yuantus.meta_engine.web.report_definition_router",
    ("GET", "/api/v1/reports/definitions"): "yuantus.meta_engine.web.report_definition_router",
    ("GET", "/api/v1/reports/definitions/{report_id}"): "yuantus.meta_engine.web.report_definition_router",
    ("PATCH", "/api/v1/reports/definitions/{report_id}"): "yuantus.meta_engine.web.report_definition_router",
    ("DELETE", "/api/v1/reports/definitions/{report_id}"): "yuantus.meta_engine.web.report_definition_router",
    ("POST", "/api/v1/reports/definitions/{report_id}/execute"): "yuantus.meta_engine.web.report_definition_router",
    ("POST", "/api/v1/reports/definitions/{report_id}/export"): "yuantus.meta_engine.web.report_definition_router",
    ("GET", "/api/v1/reports/executions"): "yuantus.meta_engine.web.report_definition_router",
    ("GET", "/api/v1/reports/executions/{execution_id}"): "yuantus.meta_engine.web.report_definition_router",
    ("POST", "/api/v1/reports/dashboards"): "yuantus.meta_engine.web.report_dashboard_router",
    ("GET", "/api/v1/reports/dashboards"): "yuantus.meta_engine.web.report_dashboard_router",
    ("GET", "/api/v1/reports/dashboards/{dashboard_id}"): "yuantus.meta_engine.web.report_dashboard_router",
    ("PATCH", "/api/v1/reports/dashboards/{dashboard_id}"): "yuantus.meta_engine.web.report_dashboard_router",
    ("DELETE", "/api/v1/reports/dashboards/{dashboard_id}"): "yuantus.meta_engine.web.report_dashboard_router",
}

_ROUTER_REGISTRATION_ORDER = [
    "report_saved_search_router",
    "report_summary_search_router",
    "report_definition_router",
    "report_dashboard_router",
    "report_router",
]


def _is_report_route(path: str) -> bool:
    return path == "/api/v1/reports" or path.startswith("/api/v1/reports/")


def _app_report_routes() -> dict[tuple[str, str], str]:
    routes: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_report_route(route.path):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            routes[(method, route.path)] = route.endpoint.__module__
    return routes


def test_all_report_routes_have_explicit_split_router_owner() -> None:
    assert _app_report_routes() == _EXPECTED_REPORT_ROUTE_OWNERS


def test_all_report_routes_are_registered_exactly_once() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_report_route(route.path):
            continue
        for method in route.methods or set():
            if method != "HEAD":
                counts[(method, route.path)] += 1

    assert set(counts) == set(_EXPECTED_REPORT_ROUTE_OWNERS)
    assert all(count == 1 for count in counts.values())


def test_legacy_report_router_module_is_registered_shell_only() -> None:
    text = Path(report_shim_module.__file__).read_text(encoding="utf-8")
    assert re.findall(r"@report_router\.(get|post|delete|put|patch)\(", text) == []
    assert "report_router = APIRouter" in text


def test_app_registers_report_routers_in_decomposition_order_before_legacy_shell() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")

    positions = [
        text.find(f"app.include_router({router_name}") for router_name in _ROUTER_REGISTRATION_ORDER
    ]
    assert all(position != -1 for position in positions)
    assert positions == sorted(positions)


def test_legacy_report_router_owns_no_runtime_paths() -> None:
    leaked = sorted(
        (method, path, owner)
        for (method, path), owner in _app_report_routes().items()
        if owner == "yuantus.meta_engine.web.report_router"
    )
    assert leaked == []
