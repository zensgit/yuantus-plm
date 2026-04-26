from __future__ import annotations

import re
from pathlib import Path
from typing import Set, Tuple

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import document_sync_retention_router as retention_module
from yuantus.meta_engine.web import document_sync_router as legacy_module


MOVED_ROUTES: Set[Tuple[str, str]] = {
    ("GET", "/api/v1/document-sync/checkpoints/overview"),
    ("GET", "/api/v1/document-sync/retention/summary"),
    ("GET", "/api/v1/document-sync/sites/{site_id}/checkpoints"),
    ("GET", "/api/v1/document-sync/export/retention"),
}

EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.document_sync_retention_router"


def _collect_app_routes() -> list[tuple[frozenset[str], str, str, list[str]]]:
    entries = []
    for route in create_app().routes:
        if isinstance(route, APIRoute):
            entries.append(
                (
                    frozenset(route.methods or []),
                    route.path,
                    route.endpoint.__module__,
                    list(route.tags or []),
                )
            )
    return entries


def test_moved_routes_are_owned_by_document_sync_retention_router() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for methods, path, module, _tags in _collect_app_routes():
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                resolved[key] = module

    assert sorted(MOVED_ROUTES - set(resolved)) == []
    assert {
        key: module for key, module in resolved.items() if module != EXPECTED_OWNER_MODULE
    } == {}


def test_moved_routes_are_absent_from_legacy_document_sync_router() -> None:
    source = Path(legacy_module.__file__).read_text(encoding="utf-8")
    moved_paths = {
        "/checkpoints/overview",
        "/retention/summary",
        "/sites/{site_id}/checkpoints",
        "/export/retention",
    }
    pattern = re.compile(
        r'@document_sync_router\.(get|post|delete|put|patch)\([^)]*"([^"]+)"',
        re.DOTALL,
    )

    leaked = [
        (method.upper(), path)
        for method, path in pattern.findall(source)
        if path in moved_paths
    ]
    assert leaked == []


def test_document_sync_retention_router_is_registered_in_app() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    source = app_py.read_text(encoding="utf-8")

    retention_pos = source.find("app.include_router(document_sync_retention_router")
    assert retention_pos != -1, "document_sync_retention_router must be registered in app.py"
    assert "app.include_router(document_sync_router," not in source, (
        "Legacy document_sync_router shell must not be registered after Phase 1 P1.10"
    )


def test_each_moved_document_sync_retention_path_is_registered_exactly_once() -> None:
    counts: dict[tuple[str, str], int] = {}
    for methods, path, _module, _tags in _collect_app_routes():
        for method in methods:
            key = (method, path)
            if key in MOVED_ROUTES:
                counts[key] = counts.get(key, 0) + 1

    assert sorted(key for key, count in counts.items() if count > 1) == []
    assert sorted(MOVED_ROUTES - set(counts)) == []


def test_moved_document_sync_retention_routes_preserve_tag() -> None:
    for methods, path, _module, tags in _collect_app_routes():
        for method in methods:
            if (method, path) in MOVED_ROUTES:
                assert "Document Sync" in tags


def test_document_sync_retention_router_source_declares_exactly_r6_routes() -> None:
    source = Path(retention_module.__file__).read_text(encoding="utf-8")
    declared_paths = [
        path
        for _method, path in re.findall(
            r'@document_sync_retention_router\.(get|post|delete|put|patch)\("([^"]+)"',
            source,
        )
    ]

    assert declared_paths == [
        "/checkpoints/overview",
        "/retention/summary",
        "/sites/{site_id}/checkpoints",
        "/export/retention",
    ]
