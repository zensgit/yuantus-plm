from __future__ import annotations

from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api import app as app_module
from yuantus.api.app import create_app
from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router


def _route_keys(router) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            keys.add((method, route.path))
    return keys


def test_legacy_parallel_tasks_router_remains_empty_import_surface():
    assert _route_keys(parallel_tasks_router) == set()


def test_create_app_no_longer_registers_legacy_parallel_tasks_router():
    source = Path(app_module.__file__).read_text()

    assert "from yuantus.meta_engine.web.parallel_tasks_router import" not in source
    assert "include_router(parallel_tasks_router" not in source


def test_create_app_still_registers_split_parallel_task_routes():
    app = create_app()
    paths = {
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
    }

    assert "/api/v1/doc-sync/jobs" in paths
    assert "/api/v1/breakages" in paths
    assert "/api/v1/parallel-ops/summary" in paths
    assert "/api/v1/cad-3d/overlays" in paths
    assert "/api/v1/workorder-docs/links" in paths
    assert "/api/v1/consumption/plans" in paths
    assert "/api/v1/workflow-actions/rules" in paths
    assert "/api/v1/eco-activities/{eco_id}" in paths
