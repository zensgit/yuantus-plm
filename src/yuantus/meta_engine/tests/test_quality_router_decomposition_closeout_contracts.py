from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import quality_router as legacy_module


EXPECTED_OWNERS = {
    ("POST", "/api/v1/quality/points"): "yuantus.meta_engine.web.quality_points_router",
    ("GET", "/api/v1/quality/points"): "yuantus.meta_engine.web.quality_points_router",
    ("GET", "/api/v1/quality/points/{point_id}"): "yuantus.meta_engine.web.quality_points_router",
    ("PATCH", "/api/v1/quality/points/{point_id}"): "yuantus.meta_engine.web.quality_points_router",
    ("POST", "/api/v1/quality/checks"): "yuantus.meta_engine.web.quality_checks_router",
    ("POST", "/api/v1/quality/checks/{check_id}/record"): "yuantus.meta_engine.web.quality_checks_router",
    ("GET", "/api/v1/quality/checks"): "yuantus.meta_engine.web.quality_checks_router",
    ("GET", "/api/v1/quality/checks/{check_id}"): "yuantus.meta_engine.web.quality_checks_router",
    ("POST", "/api/v1/quality/alerts"): "yuantus.meta_engine.web.quality_alerts_router",
    ("POST", "/api/v1/quality/alerts/{alert_id}/transition"): "yuantus.meta_engine.web.quality_alerts_router",
    ("GET", "/api/v1/quality/alerts"): "yuantus.meta_engine.web.quality_alerts_router",
    ("GET", "/api/v1/quality/alerts/{alert_id}"): "yuantus.meta_engine.web.quality_alerts_router",
    ("GET", "/api/v1/quality/alerts/{alert_id}/manufacturing-context"): "yuantus.meta_engine.web.quality_alerts_router",
}


def test_legacy_quality_router_is_empty_shell() -> None:
    text = Path(legacy_module.__file__).read_text(encoding="utf-8")
    decorators = re.findall(
        r"@quality_router\.(get|post|delete|put|patch)\(",
        text,
    )
    assert decorators == []


def test_core_quality_routes_are_owned_by_split_routers() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path not in {path for _, path in EXPECTED_OWNERS}:
            continue
        for method in route.methods or []:
            key = (method, route.path)
            if key in EXPECTED_OWNERS:
                resolved[key] = route.endpoint.__module__

    assert resolved == EXPECTED_OWNERS


def test_each_core_quality_route_is_registered_exactly_once() -> None:
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


def test_quality_split_routers_registered_before_legacy_quality_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    legacy_pos = text.find("app.include_router(quality_router")
    split_positions = [
        text.find("app.include_router(quality_points_router"),
        text.find("app.include_router(quality_checks_router"),
        text.find("app.include_router(quality_alerts_router"),
    ]
    assert legacy_pos != -1
    assert all(pos != -1 and pos < legacy_pos for pos in split_positions)


def test_core_quality_routes_preserve_quality_tag() -> None:
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in EXPECTED_OWNERS:
                assert "Quality" in (route.tags or [])
