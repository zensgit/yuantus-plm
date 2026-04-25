from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import approval_ops_router as approval_ops_module
from yuantus.meta_engine.web import approvals_router as approvals_legacy_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/approvals/summary"),
    ("GET", "/api/v1/approvals/summary/export"),
    ("GET", "/api/v1/approvals/ops-report"),
    ("GET", "/api/v1/approvals/ops-report/export"),
    ("GET", "/api/v1/approvals/queue-health"),
    ("GET", "/api/v1/approvals/queue-health/export"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.approval_ops_router"


def _collect_app_routes(app):
    entries = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            entries.append((frozenset(route.methods or []), route.path, route.endpoint.__module__))
    return entries


def test_moved_routes_are_owned_by_approval_ops_router() -> None:
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


def test_moved_routes_are_absent_from_legacy_approvals_router() -> None:
    text = Path(approvals_legacy_module.__file__).read_text(encoding="utf-8")
    pattern = re.compile(r'@approvals_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"', re.DOTALL)
    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(text)
        if path.startswith("/summary") or path.startswith("/ops-report") or path.startswith("/queue-health")
    ]
    assert leaked == []


def test_approval_ops_router_registered_before_legacy_shell() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    split_pos = text.find("app.include_router(approval_ops_router")
    legacy_pos = text.find("app.include_router(approvals_router")
    assert split_pos != -1
    assert legacy_pos != -1
    assert split_pos < legacy_pos


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


def test_moved_routes_preserve_approvals_tag() -> None:
    app = create_app()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if (method, route.path) in MOVED_ROUTES:
                assert "Approvals" in (route.tags or [])


def test_ops_route_source_order_stays_summary_then_ops_then_queue_health() -> None:
    text = Path(approval_ops_module.__file__).read_text(encoding="utf-8")
    summary_idx = text.find('"/summary"')
    ops_idx = text.find('"/ops-report"')
    queue_idx = text.find('"/queue-health"')
    assert summary_idx != -1
    assert ops_idx != -1
    assert queue_idx != -1
    assert summary_idx < ops_idx < queue_idx
