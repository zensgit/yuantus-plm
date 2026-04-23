from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import eco_router as eco_shim_module


_EXPECTED_ECO_ROUTE_OWNERS = {
    ("GET", "/api/v1/eco/approvals/dashboard/summary"): "yuantus.meta_engine.web.eco_approval_ops_router",
    ("GET", "/api/v1/eco/approvals/dashboard/items"): "yuantus.meta_engine.web.eco_approval_ops_router",
    ("GET", "/api/v1/eco/approvals/dashboard/export"): "yuantus.meta_engine.web.eco_approval_ops_router",
    ("GET", "/api/v1/eco/approvals/audit/anomalies"): "yuantus.meta_engine.web.eco_approval_ops_router",
    ("GET", "/api/v1/eco/stages"): "yuantus.meta_engine.web.eco_stage_router",
    ("POST", "/api/v1/eco/stages"): "yuantus.meta_engine.web.eco_stage_router",
    ("PUT", "/api/v1/eco/stages/{stage_id}"): "yuantus.meta_engine.web.eco_stage_router",
    ("DELETE", "/api/v1/eco/stages/{stage_id}"): "yuantus.meta_engine.web.eco_stage_router",
    ("GET", "/api/v1/eco/approvals/pending"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("POST", "/api/v1/eco/approvals/batch"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("GET", "/api/v1/eco/approvals/overdue"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("POST", "/api/v1/eco/approvals/notify-overdue"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("GET", "/api/v1/eco/{eco_id}/approval-routing"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("POST", "/api/v1/eco/{eco_id}/auto-assign-approvers"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("POST", "/api/v1/eco/approvals/escalate-overdue"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("POST", "/api/v1/eco/{eco_id}/approve"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("POST", "/api/v1/eco/{eco_id}/reject"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("GET", "/api/v1/eco/{eco_id}/approvals"): "yuantus.meta_engine.web.eco_approval_workflow_router",
    ("GET", "/api/v1/eco/{eco_id}/impact"): "yuantus.meta_engine.web.eco_impact_apply_router",
    ("GET", "/api/v1/eco/{eco_id}/impact/export"): "yuantus.meta_engine.web.eco_impact_apply_router",
    ("GET", "/api/v1/eco/{eco_id}/bom-diff"): "yuantus.meta_engine.web.eco_impact_apply_router",
    ("POST", "/api/v1/eco/{eco_id}/apply"): "yuantus.meta_engine.web.eco_impact_apply_router",
    ("GET", "/api/v1/eco/{eco_id}/apply-diagnostics"): "yuantus.meta_engine.web.eco_impact_apply_router",
    ("GET", "/api/v1/eco/{eco_id}/routing-changes"): "yuantus.meta_engine.web.eco_change_analysis_router",
    ("POST", "/api/v1/eco/{eco_id}/compute-routing-changes"): "yuantus.meta_engine.web.eco_change_analysis_router",
    ("GET", "/api/v1/eco/{eco_id}/changes"): "yuantus.meta_engine.web.eco_change_analysis_router",
    ("POST", "/api/v1/eco/{eco_id}/compute-changes"): "yuantus.meta_engine.web.eco_change_analysis_router",
    ("GET", "/api/v1/eco/{eco_id}/conflicts"): "yuantus.meta_engine.web.eco_change_analysis_router",
    ("POST", "/api/v1/eco/{eco_id}/cancel"): "yuantus.meta_engine.web.eco_lifecycle_router",
    ("GET", "/api/v1/eco/{eco_id}/unsuspend-diagnostics"): "yuantus.meta_engine.web.eco_lifecycle_router",
    ("POST", "/api/v1/eco/{eco_id}/suspend"): "yuantus.meta_engine.web.eco_lifecycle_router",
    ("POST", "/api/v1/eco/{eco_id}/unsuspend"): "yuantus.meta_engine.web.eco_lifecycle_router",
    ("POST", "/api/v1/eco/{eco_id}/move-stage"): "yuantus.meta_engine.web.eco_lifecycle_router",
    ("GET", "/api/v1/eco/kanban"): "yuantus.meta_engine.web.eco_core_router",
    ("POST", "/api/v1/eco"): "yuantus.meta_engine.web.eco_core_router",
    ("GET", "/api/v1/eco"): "yuantus.meta_engine.web.eco_core_router",
    ("GET", "/api/v1/eco/{eco_id}"): "yuantus.meta_engine.web.eco_core_router",
    ("POST", "/api/v1/eco/{eco_id}/bind-product"): "yuantus.meta_engine.web.eco_core_router",
    ("PUT", "/api/v1/eco/{eco_id}"): "yuantus.meta_engine.web.eco_core_router",
    ("DELETE", "/api/v1/eco/{eco_id}"): "yuantus.meta_engine.web.eco_core_router",
    ("POST", "/api/v1/eco/{eco_id}/new-revision"): "yuantus.meta_engine.web.eco_core_router",
}

_ROUTER_REGISTRATION_ORDER = [
    "eco_approval_ops_router",
    "eco_stage_router",
    "eco_approval_workflow_router",
    "eco_impact_apply_router",
    "eco_change_analysis_router",
    "eco_lifecycle_router",
    "eco_core_router",
]


def _is_eco_route(path: str) -> bool:
    return path == "/api/v1/eco" or path.startswith("/api/v1/eco/")


def _app_eco_routes() -> dict[tuple[str, str], str]:
    routes: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_eco_route(route.path):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            routes[(method, route.path)] = route.endpoint.__module__
    return routes


def test_all_eco_routes_have_explicit_split_router_owner() -> None:
    assert _app_eco_routes() == _EXPECTED_ECO_ROUTE_OWNERS


def test_all_eco_routes_are_registered_exactly_once() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_eco_route(route.path):
            continue
        for method in route.methods or set():
            if method != "HEAD":
                counts[(method, route.path)] += 1

    assert set(counts) == set(_EXPECTED_ECO_ROUTE_OWNERS)
    assert all(count == 1 for count in counts.values())


def test_legacy_eco_router_module_is_shim_only() -> None:
    text = Path(eco_shim_module.__file__).read_text(encoding="utf-8")
    assert re.findall(r"@eco_router\.(get|post|delete|put|patch)\(", text) == []
    assert "eco_core_router as eco_router" in text


def test_app_registers_specialized_eco_routers_before_core_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    positions = [
        text.find(f"app.include_router({router_name}") for router_name in _ROUTER_REGISTRATION_ORDER
    ]

    assert all(position != -1 for position in positions)
    assert positions == sorted(positions)
    assert "app.include_router(eco_router" not in text


def test_parallel_eco_activities_are_outside_eco_decomposition_scope() -> None:
    assert not any(
        path.startswith("/api/v1/eco-activities")
        for _method, path in _EXPECTED_ECO_ROUTE_OWNERS
    )
