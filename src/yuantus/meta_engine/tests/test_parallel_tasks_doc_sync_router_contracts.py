from __future__ import annotations

from collections import Counter

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web.parallel_tasks_doc_sync_router import (
    parallel_tasks_doc_sync_router,
)
from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router


_DOC_SYNC_ROUTE_KEYS = {
    ("POST", "/doc-sync/sites"),
    ("GET", "/doc-sync/sites"),
    ("POST", "/doc-sync/sites/{site_id}/health"),
    ("POST", "/doc-sync/jobs"),
    ("GET", "/doc-sync/jobs"),
    ("GET", "/doc-sync/jobs/dead-letter"),
    ("POST", "/doc-sync/jobs/replay-batch"),
    ("GET", "/doc-sync/summary"),
    ("GET", "/doc-sync/summary/export"),
    ("GET", "/doc-sync/jobs/{job_id}"),
    ("POST", "/doc-sync/jobs/{job_id}/replay"),
}


def _route_keys(router, *, prefix: str = "") -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            keys.add((method, f"{prefix}{route.path}"))
    return keys


def test_doc_sync_routes_owned_by_split_router():
    assert _DOC_SYNC_ROUTE_KEYS <= _route_keys(parallel_tasks_doc_sync_router)


def test_parallel_tasks_router_no_longer_owns_doc_sync_routes():
    assert not {
        path
        for _method, path in _route_keys(parallel_tasks_router)
        if path.startswith("/doc-sync")
    }


def test_create_app_registers_doc_sync_routes_once():
    app = create_app()
    counts: Counter[tuple[str, str]] = Counter()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1/doc-sync"):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            counts[(method, route.path)] += 1

    expected = {(method, f"/api/v1{path}") for method, path in _DOC_SYNC_ROUTE_KEYS}
    assert set(counts) == expected
    assert all(count == 1 for count in counts.values())
