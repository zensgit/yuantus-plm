from __future__ import annotations

from collections import Counter

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web.parallel_tasks_eco_activities_router import (
    parallel_tasks_eco_activities_router,
)
from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router


_ECO_ACTIVITIES_ROUTE_KEYS = {
    ("POST", "/eco-activities"),
    ("GET", "/eco-activities/{eco_id}"),
    ("POST", "/eco-activities/activity/{activity_id}/transition"),
    ("GET", "/eco-activities/activity/{activity_id}/transition-check"),
    ("POST", "/eco-activities/{eco_id}/transition-check/bulk"),
    ("POST", "/eco-activities/{eco_id}/transition/bulk"),
    ("GET", "/eco-activities/{eco_id}/blockers"),
    ("GET", "/eco-activities/{eco_id}/events"),
    ("GET", "/eco-activities/{eco_id}/sla"),
    ("GET", "/eco-activities/{eco_id}/sla/alerts"),
    ("GET", "/eco-activities/{eco_id}/sla/alerts/export"),
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


def test_eco_activities_routes_owned_by_split_router():
    assert _ECO_ACTIVITIES_ROUTE_KEYS <= _route_keys(
        parallel_tasks_eco_activities_router
    )


def test_parallel_tasks_router_no_longer_owns_eco_activities_routes():
    assert not {
        path
        for _method, path in _route_keys(parallel_tasks_router)
        if path.startswith("/eco-activities")
    }


def test_parallel_tasks_router_is_empty_compatibility_shell():
    assert _route_keys(parallel_tasks_router) == set()


def test_create_app_registers_eco_activities_routes_once():
    app = create_app()
    counts: Counter[tuple[str, str]] = Counter()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1/eco-activities"):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            counts[(method, route.path)] += 1

    expected = {
        (method, f"/api/v1{path}") for method, path in _ECO_ACTIVITIES_ROUTE_KEYS
    }
    assert set(counts) == expected
    assert all(count == 1 for count in counts.values())
