from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import cutted_parts_router as legacy_module


EXPECTED_OWNERS = {
    (
        "GET",
        "/api/v1/cutted-parts/throughput/overview",
    ): "yuantus.meta_engine.web.cutted_parts_throughput_router",
    (
        "GET",
        "/api/v1/cutted-parts/cadence/summary",
    ): "yuantus.meta_engine.web.cutted_parts_throughput_router",
    (
        "GET",
        "/api/v1/cutted-parts/plans/{plan_id}/cadence",
    ): "yuantus.meta_engine.web.cutted_parts_throughput_router",
    (
        "GET",
        "/api/v1/cutted-parts/export/cadence",
    ): "yuantus.meta_engine.web.cutted_parts_throughput_router",
    (
        "GET",
        "/api/v1/cutted-parts/saturation/overview",
    ): "yuantus.meta_engine.web.cutted_parts_bottlenecks_router",
    (
        "GET",
        "/api/v1/cutted-parts/bottlenecks/summary",
    ): "yuantus.meta_engine.web.cutted_parts_bottlenecks_router",
    (
        "GET",
        "/api/v1/cutted-parts/plans/{plan_id}/bottlenecks",
    ): "yuantus.meta_engine.web.cutted_parts_bottlenecks_router",
    (
        "GET",
        "/api/v1/cutted-parts/export/bottlenecks",
    ): "yuantus.meta_engine.web.cutted_parts_bottlenecks_router",
}


def test_cutted_parts_r1_routes_are_owned_by_split_routers() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            key = (method, route.path)
            if key in EXPECTED_OWNERS:
                resolved[key] = route.endpoint.__module__

    assert resolved == EXPECTED_OWNERS


def test_cutted_parts_r1_routes_are_absent_from_legacy_router() -> None:
    text = Path(legacy_module.__file__).read_text(encoding="utf-8")
    moved_literals = {
        "/throughput/overview",
        "/cadence/summary",
        "/plans/{plan_id}/cadence",
        "/export/cadence",
        "/saturation/overview",
        "/bottlenecks/summary",
        "/plans/{plan_id}/bottlenecks",
        "/export/bottlenecks",
    }
    pattern = re.compile(
        r'@cutted_parts_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"',
        re.DOTALL,
    )

    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(text)
        if path in moved_literals
    ]

    assert leaked == []


def test_cutted_parts_r1_split_routers_registered_in_app() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    throughput_pos = text.find("app.include_router(cutted_parts_throughput_router")
    bottlenecks_pos = text.find("app.include_router(cutted_parts_bottlenecks_router")

    assert throughput_pos != -1, "cutted_parts_throughput_router must be registered in app.py"
    assert bottlenecks_pos != -1, "cutted_parts_bottlenecks_router must be registered in app.py"
    assert throughput_pos < bottlenecks_pos, (
        "cutted_parts R1 source declaration order: throughput before bottlenecks"
    )
    assert "app.include_router(cutted_parts_router," not in text, (
        "Legacy cutted_parts_router shell must not be registered after Phase 1 P1.7"
    )


def test_each_cutted_parts_r1_route_is_registered_exactly_once() -> None:
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


def test_cutted_parts_r1_routes_preserve_tag() -> None:
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in EXPECTED_OWNERS:
                assert "Cutted Parts" in (route.tags or [])
