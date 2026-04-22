from __future__ import annotations

from collections import Counter

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router
from yuantus.meta_engine.web.parallel_tasks_workflow_actions_router import (
    parallel_tasks_workflow_actions_router,
)


_WORKFLOW_ACTIONS_ROUTE_KEYS = {
    ("POST", "/workflow-actions/rules"),
    ("GET", "/workflow-actions/rules"),
    ("POST", "/workflow-actions/execute"),
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


def test_workflow_actions_routes_owned_by_split_router():
    assert _WORKFLOW_ACTIONS_ROUTE_KEYS <= _route_keys(
        parallel_tasks_workflow_actions_router
    )


def test_parallel_tasks_router_no_longer_owns_workflow_actions_routes():
    assert not {
        path
        for _method, path in _route_keys(parallel_tasks_router)
        if path.startswith("/workflow-actions")
    }


def test_create_app_registers_workflow_actions_routes_once():
    app = create_app()
    counts: Counter[tuple[str, str]] = Counter()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1/workflow-actions"):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            counts[(method, route.path)] += 1

    expected = {
        (method, f"/api/v1{path}") for method, path in _WORKFLOW_ACTIONS_ROUTE_KEYS
    }
    assert set(counts) == expected
    assert all(count == 1 for count in counts.values())
