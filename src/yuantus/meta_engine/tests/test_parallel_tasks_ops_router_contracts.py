from __future__ import annotations

from collections import Counter

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web.parallel_tasks_ops_router import (
    parallel_tasks_ops_router,
)
from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router


_PARALLEL_OPS_ROUTE_KEYS = {
    ("GET", "/parallel-ops/summary"),
    ("GET", "/parallel-ops/trends"),
    ("GET", "/parallel-ops/alerts"),
    ("GET", "/parallel-ops/summary/export"),
    ("GET", "/parallel-ops/trends/export"),
    ("GET", "/parallel-ops/doc-sync/failures"),
    ("GET", "/parallel-ops/workflow/failures"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/trends"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/triage"),
    ("POST", "/parallel-ops/breakage-helpdesk/failures/triage/apply"),
    ("POST", "/parallel-ops/breakage-helpdesk/failures/replay/enqueue"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/replay/batches"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/replay/trends"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/replay/trends/export"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}"),
    (
        "GET",
        "/parallel-ops/breakage-helpdesk/failures/replay/batches/{batch_id}/export",
    ),
    ("POST", "/parallel-ops/breakage-helpdesk/failures/replay/batches/cleanup"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/export"),
    ("POST", "/parallel-ops/breakage-helpdesk/failures/export/jobs"),
    ("POST", "/parallel-ops/breakage-helpdesk/failures/export/jobs/cleanup"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/export/jobs/overview"),
    ("GET", "/parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}"),
    ("POST", "/parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}/run"),
    (
        "GET",
        "/parallel-ops/breakage-helpdesk/failures/export/jobs/{job_id}/download",
    ),
    ("GET", "/parallel-ops/metrics"),
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


def test_parallel_ops_routes_owned_by_split_router():
    assert _PARALLEL_OPS_ROUTE_KEYS <= _route_keys(parallel_tasks_ops_router)


def test_parallel_tasks_router_no_longer_owns_parallel_ops_routes():
    assert not {
        path
        for _method, path in _route_keys(parallel_tasks_router)
        if path.startswith("/parallel-ops")
    }


def test_create_app_registers_parallel_ops_routes_once():
    app = create_app()
    counts: Counter[tuple[str, str]] = Counter()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1/parallel-ops"):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            counts[(method, route.path)] += 1

    expected = {
        (method, f"/api/v1{path}") for method, path in _PARALLEL_OPS_ROUTE_KEYS
    }
    assert set(counts) == expected
    assert all(count == 1 for count in counts.values())
