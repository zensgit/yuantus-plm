from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import cutted_parts_router as legacy_module


CORE = "yuantus.meta_engine.web.cutted_parts_core_router"
ANALYTICS = "yuantus.meta_engine.web.cutted_parts_analytics_router"
UTILIZATION = "yuantus.meta_engine.web.cutted_parts_utilization_router"
SCENARIOS = "yuantus.meta_engine.web.cutted_parts_scenarios_router"
BENCHMARK = "yuantus.meta_engine.web.cutted_parts_benchmark_router"
VARIANCE = "yuantus.meta_engine.web.cutted_parts_variance_router"
THRESHOLDS = "yuantus.meta_engine.web.cutted_parts_thresholds_router"
ALERTS = "yuantus.meta_engine.web.cutted_parts_alerts_router"
THROUGHPUT = "yuantus.meta_engine.web.cutted_parts_throughput_router"
BOTTLENECKS = "yuantus.meta_engine.web.cutted_parts_bottlenecks_router"


EXPECTED_OWNERS = {
    ("POST", "/api/v1/cutted-parts/plans"): CORE,
    ("GET", "/api/v1/cutted-parts/plans"): CORE,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}"): CORE,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/summary"): CORE,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/cuts"): CORE,
    ("GET", "/api/v1/cutted-parts/materials"): CORE,
    ("GET", "/api/v1/cutted-parts/overview"): ANALYTICS,
    ("GET", "/api/v1/cutted-parts/materials/analytics"): ANALYTICS,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/waste-summary"): ANALYTICS,
    ("GET", "/api/v1/cutted-parts/export/overview"): ANALYTICS,
    ("GET", "/api/v1/cutted-parts/export/waste"): ANALYTICS,
    ("GET", "/api/v1/cutted-parts/utilization/overview"): UTILIZATION,
    ("GET", "/api/v1/cutted-parts/materials/utilization"): UTILIZATION,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/cost-summary"): UTILIZATION,
    ("GET", "/api/v1/cutted-parts/export/utilization"): UTILIZATION,
    ("GET", "/api/v1/cutted-parts/export/costs"): UTILIZATION,
    ("GET", "/api/v1/cutted-parts/templates/overview"): SCENARIOS,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/scenarios"): SCENARIOS,
    ("GET", "/api/v1/cutted-parts/materials/templates"): SCENARIOS,
    ("GET", "/api/v1/cutted-parts/export/scenarios"): SCENARIOS,
    ("GET", "/api/v1/cutted-parts/benchmark/overview"): BENCHMARK,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/quote-summary"): BENCHMARK,
    ("GET", "/api/v1/cutted-parts/materials/benchmarks"): BENCHMARK,
    ("GET", "/api/v1/cutted-parts/export/quotes"): BENCHMARK,
    ("GET", "/api/v1/cutted-parts/variance/overview"): VARIANCE,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/recommendations"): VARIANCE,
    ("GET", "/api/v1/cutted-parts/materials/variance"): VARIANCE,
    ("GET", "/api/v1/cutted-parts/export/recommendations"): VARIANCE,
    ("GET", "/api/v1/cutted-parts/thresholds/overview"): THRESHOLDS,
    ("GET", "/api/v1/cutted-parts/envelopes/summary"): THRESHOLDS,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/threshold-check"): THRESHOLDS,
    ("GET", "/api/v1/cutted-parts/export/envelopes"): THRESHOLDS,
    ("GET", "/api/v1/cutted-parts/alerts/overview"): ALERTS,
    ("GET", "/api/v1/cutted-parts/outliers/summary"): ALERTS,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/alerts"): ALERTS,
    ("GET", "/api/v1/cutted-parts/export/outliers"): ALERTS,
    ("GET", "/api/v1/cutted-parts/throughput/overview"): THROUGHPUT,
    ("GET", "/api/v1/cutted-parts/cadence/summary"): THROUGHPUT,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/cadence"): THROUGHPUT,
    ("GET", "/api/v1/cutted-parts/export/cadence"): THROUGHPUT,
    ("GET", "/api/v1/cutted-parts/saturation/overview"): BOTTLENECKS,
    ("GET", "/api/v1/cutted-parts/bottlenecks/summary"): BOTTLENECKS,
    ("GET", "/api/v1/cutted-parts/plans/{plan_id}/bottlenecks"): BOTTLENECKS,
    ("GET", "/api/v1/cutted-parts/export/bottlenecks"): BOTTLENECKS,
}


def test_legacy_cutted_parts_router_is_empty_shell() -> None:
    text = Path(legacy_module.__file__).read_text(encoding="utf-8")
    decorators = re.findall(
        r"@cutted_parts_router\.(get|post|delete|put|patch)\(",
        text,
    )
    assert decorators == []


def test_all_cutted_parts_routes_are_owned_by_split_routers() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            key = (method, route.path)
            if key in EXPECTED_OWNERS:
                resolved[key] = route.endpoint.__module__

    assert resolved == EXPECTED_OWNERS


def test_each_cutted_parts_route_is_registered_exactly_once() -> None:
    counts: dict[tuple[str, str], int] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            key = (method, route.path)
            if key in EXPECTED_OWNERS:
                counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(key for key, count in counts.items() if count > 1)
    missing = sorted(set(EXPECTED_OWNERS) - set(counts))
    assert duplicates == []
    assert missing == []


def test_cutted_parts_split_routers_registered_before_legacy_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    legacy_pos = text.find("app.include_router(cutted_parts_router")
    split_tokens = [
        "app.include_router(cutted_parts_analytics_router",
        "app.include_router(cutted_parts_utilization_router",
        "app.include_router(cutted_parts_scenarios_router",
        "app.include_router(cutted_parts_benchmark_router",
        "app.include_router(cutted_parts_variance_router",
        "app.include_router(cutted_parts_thresholds_router",
        "app.include_router(cutted_parts_alerts_router",
        "app.include_router(cutted_parts_throughput_router",
        "app.include_router(cutted_parts_bottlenecks_router",
        "app.include_router(cutted_parts_core_router",
    ]
    split_positions = [text.find(token) for token in split_tokens]

    assert legacy_pos != -1
    assert all(pos != -1 and pos < legacy_pos for pos in split_positions)


def test_cutted_parts_routes_preserve_tag() -> None:
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in EXPECTED_OWNERS:
                assert "Cutted Parts" in (route.tags or [])
