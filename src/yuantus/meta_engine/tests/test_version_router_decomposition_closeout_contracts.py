from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import version_router as legacy_module


EXPECTED_OWNERS = {
    ("POST", "/api/v1/versions/schemes"): "yuantus.meta_engine.web.version_revision_router",
    ("GET", "/api/v1/versions/schemes"): "yuantus.meta_engine.web.version_revision_router",
    ("GET", "/api/v1/versions/schemes/for-type/{item_type_id}"): "yuantus.meta_engine.web.version_revision_router",
    ("GET", "/api/v1/versions/revision/next"): "yuantus.meta_engine.web.version_revision_router",
    ("GET", "/api/v1/versions/revision/parse"): "yuantus.meta_engine.web.version_revision_router",
    ("GET", "/api/v1/versions/revision/compare"): "yuantus.meta_engine.web.version_revision_router",
    ("POST", "/api/v1/versions/{version_id}/iterations"): "yuantus.meta_engine.web.version_iteration_router",
    ("GET", "/api/v1/versions/{version_id}/iterations"): "yuantus.meta_engine.web.version_iteration_router",
    ("GET", "/api/v1/versions/{version_id}/iterations/latest"): "yuantus.meta_engine.web.version_iteration_router",
    ("POST", "/api/v1/versions/iterations/{iteration_id}/restore"): "yuantus.meta_engine.web.version_iteration_router",
    ("DELETE", "/api/v1/versions/iterations/{iteration_id}"): "yuantus.meta_engine.web.version_iteration_router",
    ("GET", "/api/v1/versions/{version_id}/detail"): "yuantus.meta_engine.web.version_file_router",
    ("POST", "/api/v1/versions/{version_id}/files"): "yuantus.meta_engine.web.version_file_router",
    ("DELETE", "/api/v1/versions/{version_id}/files/{file_id}"): "yuantus.meta_engine.web.version_file_router",
    ("GET", "/api/v1/versions/{version_id}/files"): "yuantus.meta_engine.web.version_file_router",
    ("POST", "/api/v1/versions/{version_id}/files/{file_id}/checkout"): "yuantus.meta_engine.web.version_file_router",
    ("POST", "/api/v1/versions/{version_id}/files/{file_id}/undo-checkout"): "yuantus.meta_engine.web.version_file_router",
    ("GET", "/api/v1/versions/{version_id}/files/{file_id}/lock"): "yuantus.meta_engine.web.version_file_router",
    ("PUT", "/api/v1/versions/{version_id}/files/primary"): "yuantus.meta_engine.web.version_file_router",
    ("PUT", "/api/v1/versions/{version_id}/thumbnail"): "yuantus.meta_engine.web.version_file_router",
    ("GET", "/api/v1/versions/compare-full"): "yuantus.meta_engine.web.version_file_router",
    ("GET", "/api/v1/versions/items/{item_id}/tree-full"): "yuantus.meta_engine.web.version_file_router",
    ("POST", "/api/v1/versions/items/{item_id}/init"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("POST", "/api/v1/versions/items/{item_id}/checkout"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("POST", "/api/v1/versions/items/{item_id}/checkin"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("POST", "/api/v1/versions/items/{item_id}/merge"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("GET", "/api/v1/versions/compare"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("POST", "/api/v1/versions/items/{item_id}/revise"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("GET", "/api/v1/versions/items/{item_id}/history"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("POST", "/api/v1/versions/items/{item_id}/branch"): "yuantus.meta_engine.web.version_lifecycle_router",
    ("POST", "/api/v1/versions/{version_id}/effectivity"): "yuantus.meta_engine.web.version_effectivity_router",
    ("GET", "/api/v1/versions/items/{item_id}/effective"): "yuantus.meta_engine.web.version_effectivity_router",
    ("GET", "/api/v1/versions/items/{item_id}/tree"): "yuantus.meta_engine.web.version_effectivity_router",
}


def test_legacy_version_router_is_empty_shell() -> None:
    text = Path(legacy_module.__file__).read_text(encoding="utf-8")
    decorators = re.findall(
        r"@version_router\.(get|post|delete|put|patch)\(",
        text,
    )
    assert decorators == []


def test_all_version_routes_are_owned_by_split_routers() -> None:
    resolved: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1/versions"):
            continue
        for method in route.methods or []:
            resolved[(method, route.path)] = route.endpoint.__module__

    assert resolved == EXPECTED_OWNERS


def test_version_legacy_shell_registered_last() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    legacy_pos = text.find("app.include_router(version_router")
    split_positions = [
        text.find("app.include_router(version_revision_router"),
        text.find("app.include_router(version_iteration_router"),
        text.find("app.include_router(version_file_router"),
        text.find("app.include_router(version_lifecycle_router"),
        text.find("app.include_router(version_effectivity_router"),
    ]
    assert legacy_pos != -1
    assert all(pos != -1 and pos < legacy_pos for pos in split_positions)
