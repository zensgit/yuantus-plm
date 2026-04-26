from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import box_router as legacy_module


CORE = "yuantus.meta_engine.web.box_core_router"
ANALYTICS = "yuantus.meta_engine.web.box_analytics_router"
OPS = "yuantus.meta_engine.web.box_ops_router"
RECONCILIATION = "yuantus.meta_engine.web.box_reconciliation_router"
CAPACITY = "yuantus.meta_engine.web.box_capacity_router"
POLICY = "yuantus.meta_engine.web.box_policy_router"
TRACEABILITY = "yuantus.meta_engine.web.box_traceability_router"
CUSTODY = "yuantus.meta_engine.web.box_custody_router"
TURNOVER = "yuantus.meta_engine.web.box_turnover_router"
AGING = "yuantus.meta_engine.web.box_aging_router"


EXPECTED_OWNERS = {
    ("POST", "/api/v1/box/items"): CORE,
    ("GET", "/api/v1/box/items"): CORE,
    ("GET", "/api/v1/box/items/{box_id}"): CORE,
    ("GET", "/api/v1/box/items/{box_id}/contents"): CORE,
    ("GET", "/api/v1/box/items/{box_id}/export-meta"): CORE,
    ("GET", "/api/v1/box/overview"): ANALYTICS,
    ("GET", "/api/v1/box/materials/analytics"): ANALYTICS,
    ("GET", "/api/v1/box/items/{box_id}/contents-summary"): ANALYTICS,
    ("GET", "/api/v1/box/export/overview"): ANALYTICS,
    ("GET", "/api/v1/box/items/{box_id}/export-contents"): ANALYTICS,
    ("GET", "/api/v1/box/transitions/summary"): OPS,
    ("GET", "/api/v1/box/active-archive/breakdown"): OPS,
    ("GET", "/api/v1/box/items/{box_id}/ops-report"): OPS,
    ("GET", "/api/v1/box/export/ops-report"): OPS,
    ("GET", "/api/v1/box/reconciliation/overview"): RECONCILIATION,
    ("GET", "/api/v1/box/audit/summary"): RECONCILIATION,
    ("GET", "/api/v1/box/items/{box_id}/reconciliation"): RECONCILIATION,
    ("GET", "/api/v1/box/export/reconciliation"): RECONCILIATION,
    ("GET", "/api/v1/box/capacity/overview"): CAPACITY,
    ("GET", "/api/v1/box/compliance/summary"): CAPACITY,
    ("GET", "/api/v1/box/items/{box_id}/capacity"): CAPACITY,
    ("GET", "/api/v1/box/export/capacity"): CAPACITY,
    ("GET", "/api/v1/box/policy/overview"): POLICY,
    ("GET", "/api/v1/box/exceptions/summary"): POLICY,
    ("GET", "/api/v1/box/items/{box_id}/policy-check"): POLICY,
    ("GET", "/api/v1/box/export/exceptions"): POLICY,
    ("GET", "/api/v1/box/reservations/overview"): TRACEABILITY,
    ("GET", "/api/v1/box/traceability/summary"): TRACEABILITY,
    ("GET", "/api/v1/box/items/{box_id}/reservations"): TRACEABILITY,
    ("GET", "/api/v1/box/export/traceability"): TRACEABILITY,
    ("GET", "/api/v1/box/allocations/overview"): CUSTODY,
    ("GET", "/api/v1/box/custody/summary"): CUSTODY,
    ("GET", "/api/v1/box/items/{box_id}/custody"): CUSTODY,
    ("GET", "/api/v1/box/export/custody"): CUSTODY,
    ("GET", "/api/v1/box/occupancy/overview"): TURNOVER,
    ("GET", "/api/v1/box/turnover/summary"): TURNOVER,
    ("GET", "/api/v1/box/items/{box_id}/turnover"): TURNOVER,
    ("GET", "/api/v1/box/export/turnover"): TURNOVER,
    ("GET", "/api/v1/box/dwell/overview"): AGING,
    ("GET", "/api/v1/box/aging/summary"): AGING,
    ("GET", "/api/v1/box/items/{box_id}/aging"): AGING,
    ("GET", "/api/v1/box/export/aging"): AGING,
}


def test_legacy_box_router_is_empty_shell() -> None:
    text = Path(legacy_module.__file__).read_text(encoding="utf-8")
    decorators = re.findall(r"@box_router\.(get|post|delete|put|patch)\(", text)
    assert decorators == []


def test_all_box_routes_are_owned_by_split_routers() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            key = (method, route.path)
            if key in EXPECTED_OWNERS:
                resolved[key] = route.endpoint.__module__

    assert resolved == EXPECTED_OWNERS


def test_each_box_route_is_registered_exactly_once() -> None:
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


def test_box_split_routers_registered_in_app() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    split_tokens = [
        "app.include_router(box_core_router",
        "app.include_router(box_analytics_router",
        "app.include_router(box_ops_router",
        "app.include_router(box_reconciliation_router",
        "app.include_router(box_capacity_router",
        "app.include_router(box_policy_router",
        "app.include_router(box_traceability_router",
        "app.include_router(box_custody_router",
        "app.include_router(box_turnover_router",
        "app.include_router(box_aging_router",
    ]
    split_positions = [text.find(token) for token in split_tokens]
    assert all(pos != -1 for pos in split_positions), (
        "All 10 box split routers must be registered in app.py"
    )
    assert "app.include_router(box_router," not in text, (
        "Legacy box_router shell must not be registered after Phase 1 P1.6"
    )


def test_box_routes_preserve_tag() -> None:
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in EXPECTED_OWNERS:
                assert "PLM Box" in (route.tags or [])
