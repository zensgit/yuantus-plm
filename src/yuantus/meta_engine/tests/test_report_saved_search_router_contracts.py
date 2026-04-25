from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import report_router as report_legacy_module
from yuantus.meta_engine.web import report_saved_search_router as report_saved_search_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("POST", "/api/v1/reports/saved-searches"),
    ("GET", "/api/v1/reports/saved-searches"),
    ("GET", "/api/v1/reports/saved-searches/{saved_search_id}"),
    ("PATCH", "/api/v1/reports/saved-searches/{saved_search_id}"),
    ("DELETE", "/api/v1/reports/saved-searches/{saved_search_id}"),
    ("POST", "/api/v1/reports/saved-searches/{saved_search_id}/run"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.report_saved_search_router"


def _collect_app_routes(app):
    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__, route.tags or []))
    return entries


def test_moved_routes_are_owned_by_report_saved_search_router() -> None:
    app = create_app()
    entries = _collect_app_routes(app)

    resolved: dict[tuple[str, str], str] = {}
    for methods, path, module, _tags in entries:
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                resolved[key] = module

    missing = sorted(MOVED_ROUTES - set(resolved))
    assert not missing, f"Expected moved routes not registered: {missing}"

    wrong_owner = sorted((key, module) for key, module in resolved.items() if module != EXPECTED_OWNER_MODULE)
    assert not wrong_owner, f"Moved routes owned by unexpected modules: {wrong_owner}"


def test_moved_routes_are_absent_from_legacy_report_router() -> None:
    text = Path(report_legacy_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(r'@report_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = []
    for method, path in pattern.findall(text):
        if path.startswith("/saved-searches"):
            leaked.append((method.upper(), path))

    assert not leaked, f"report_router.py still declares saved-search routes: {leaked}"


def test_report_saved_search_router_registered_before_legacy_report_router() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    split_pos = text.find("app.include_router(report_saved_search_router")
    legacy_pos = text.find("app.include_router(report_router")

    assert split_pos != -1, "report_saved_search_router is not registered in app.py"
    assert legacy_pos != -1, "report_router is not registered in app.py"
    assert split_pos < legacy_pos, "report_saved_search_router must be registered before report_router"


def test_each_moved_path_is_registered_exactly_once() -> None:
    app = create_app()
    entries = _collect_app_routes(app)

    counts: dict[tuple[str, str], int] = {}
    for methods, path, _module, _tags in entries:
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                counts[key] = counts.get(key, 0) + 1

    duplicates = sorted(key for key, count in counts.items() if count > 1)
    missing = sorted(MOVED_ROUTES - set(counts))
    assert not duplicates, f"Duplicate registrations for: {duplicates}"
    assert not missing, f"Missing route registrations: {missing}"


def test_moved_routes_preserve_reports_tag() -> None:
    app = create_app()
    for methods, path, _module, tags in _collect_app_routes(app):
        for method in methods:
            if (method, path) in MOVED_ROUTES:
                assert "Reports" in tags, f"Route {method} {path} lost Reports tag (tags={tags})"


def test_source_declaration_order_is_preserved() -> None:
    text = Path(report_saved_search_module.__file__).read_text(encoding="utf-8")
    create_idx = text.find('@report_saved_search_router.post("/saved-searches"')
    list_idx = text.find('@report_saved_search_router.get("/saved-searches"')
    get_idx = text.find('@report_saved_search_router.get("/saved-searches/{saved_search_id}"')
    patch_idx = text.find('@report_saved_search_router.patch("/saved-searches/{saved_search_id}"')
    delete_idx = text.find('@report_saved_search_router.delete("/saved-searches/{saved_search_id}"')
    run_idx = text.find('@report_saved_search_router.post("/saved-searches/{saved_search_id}/run"')

    assert min(create_idx, list_idx, get_idx, patch_idx, delete_idx, run_idx) != -1
    assert create_idx < list_idx < get_idx < patch_idx < delete_idx < run_idx
