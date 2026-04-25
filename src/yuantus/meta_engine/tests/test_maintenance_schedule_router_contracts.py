from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import maintenance_router as legacy_module
from yuantus.meta_engine.web import maintenance_schedule_router as schedule_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/maintenance/preventive-schedule"),
    ("GET", "/api/v1/maintenance/queue-summary"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.maintenance_schedule_router"


def _collect_app_routes(app):
    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_maintenance_schedule_router() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for methods, path, module in _collect_app_routes(create_app()):
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                resolved[key] = module

    missing = sorted(MOVED_ROUTES - set(resolved))
    wrong_owner = sorted(
        (method, path, module)
        for (method, path), module in resolved.items()
        if module != EXPECTED_OWNER_MODULE
    )
    assert missing == []
    assert wrong_owner == []


def test_moved_routes_are_absent_from_legacy_maintenance_router() -> None:
    text = Path(legacy_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(r'@maintenance_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(text)
        if path in {"/preventive-schedule", "/queue-summary"}
    ]
    assert leaked == []


def test_maintenance_schedule_router_is_registered_in_app() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    split_pos = text.find("app.include_router(maintenance_schedule_router")
    assert split_pos != -1, "maintenance_schedule_router must be registered in app.py"
    assert "app.include_router(maintenance_router," not in text, (
        "Legacy maintenance_router shell must not be registered after Phase 1 P1.3"
    )


def test_each_moved_path_is_registered_exactly_once() -> None:
    counts: dict[tuple[str, str], int] = {}
    for methods, path, _module in _collect_app_routes(create_app()):
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(key for key, count in counts.items() if count > 1)
    missing = sorted(MOVED_ROUTES - set(counts))
    assert duplicates == []
    assert missing == []


def test_moved_routes_preserve_maintenance_tag() -> None:
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in MOVED_ROUTES:
                assert "Maintenance" in (route.tags or [])


def test_schedule_routes_keep_preventive_before_queue_summary() -> None:
    text = Path(schedule_module.__file__).read_text(encoding="utf-8")
    preventive_idx = text.find('"/preventive-schedule"')
    queue_idx = text.find('"/queue-summary"')
    assert preventive_idx != -1
    assert queue_idx != -1
    assert preventive_idx < queue_idx
