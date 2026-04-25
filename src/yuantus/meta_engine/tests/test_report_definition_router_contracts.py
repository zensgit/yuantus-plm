from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import report_definition_router as report_definition_module
from yuantus.meta_engine.web import report_router as report_legacy_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("POST", "/api/v1/reports/definitions"),
    ("GET", "/api/v1/reports/definitions"),
    ("GET", "/api/v1/reports/definitions/{report_id}"),
    ("PATCH", "/api/v1/reports/definitions/{report_id}"),
    ("DELETE", "/api/v1/reports/definitions/{report_id}"),
    ("POST", "/api/v1/reports/definitions/{report_id}/execute"),
    ("POST", "/api/v1/reports/definitions/{report_id}/export"),
    ("GET", "/api/v1/reports/executions"),
    ("GET", "/api/v1/reports/executions/{execution_id}"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.report_definition_router"


def _collect_app_routes(app):
    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_report_definition_router() -> None:
    app = create_app()
    entries = _collect_app_routes(app)

    resolved: dict[tuple[str, str], str] = {}
    for methods, path, module in entries:
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


def test_moved_routes_are_absent_from_legacy_report_router() -> None:
    text = Path(report_legacy_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(r'@report_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(text)
        if path.startswith("/definitions") or path.startswith("/executions")
    ]

    assert leaked == []


def test_report_definition_router_is_registered_in_app() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")

    split_pos = text.find("app.include_router(report_definition_router")
    assert split_pos != -1, "report_definition_router must be registered in app.py"
    assert "app.include_router(report_router," not in text, (
        "Legacy report_router shell must not be registered after Phase 1 P1.1"
    )


def test_each_moved_path_is_registered_exactly_once() -> None:
    app = create_app()
    entries = _collect_app_routes(app)

    counts: dict[tuple[str, str], int] = {}
    for methods, path, _module in entries:
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(key for key, count in counts.items() if count > 1)
    missing = sorted(MOVED_ROUTES - set(counts))

    assert duplicates == []
    assert missing == []


def test_moved_routes_preserve_reports_tag() -> None:
    app = create_app()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in MOVED_ROUTES:
                assert "Reports" in (route.tags or [])


def test_static_definitions_list_routes_precede_dynamic_definition_route() -> None:
    text = Path(report_definition_module.__file__).read_text(encoding="utf-8")

    list_idx = text.find('"/definitions"')
    detail_idx = text.find('"/definitions/{report_id}"')

    assert list_idx != -1
    assert detail_idx != -1
    assert list_idx < detail_idx
