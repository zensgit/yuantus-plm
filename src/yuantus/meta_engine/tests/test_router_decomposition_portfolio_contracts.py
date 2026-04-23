from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app


REPO_ROOT = Path(__file__).resolve().parents[4]
APP_PY = REPO_ROOT / "src" / "yuantus" / "api" / "app.py"
WEB_DIR = REPO_ROOT / "src" / "yuantus" / "meta_engine" / "web"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

LEGACY_ROUTER_STATES = {
    "bom_router.py": {
        "legacy_module": "yuantus.meta_engine.web.bom_router",
        "registered": True,
        "include_token": "app.include_router(bom_router",
        "import_token": "from yuantus.meta_engine.web.bom_router import bom_router",
    },
    "cad_router.py": {
        "legacy_module": "yuantus.meta_engine.web.cad_router",
        "registered": True,
        "include_token": "app.include_router(cad_router",
        "import_token": "from yuantus.meta_engine.web.cad_router import router as cad_router",
    },
    "file_router.py": {
        "legacy_module": "yuantus.meta_engine.web.file_router",
        "registered": False,
        "include_token": "app.include_router(file_router",
        "import_token": "from yuantus.meta_engine.web.file_router import file_router",
    },
    "eco_router.py": {
        "legacy_module": "yuantus.meta_engine.web.eco_router",
        "registered": False,
        "include_token": "app.include_router(eco_router",
        "import_token": "from yuantus.meta_engine.web.eco_router import",
    },
    "parallel_tasks_router.py": {
        "legacy_module": "yuantus.meta_engine.web.parallel_tasks_router",
        "registered": False,
        "include_token": "app.include_router(parallel_tasks_router",
        "import_token": "from yuantus.meta_engine.web.parallel_tasks_router import",
    },
}

CI_PORTFOLIO_ENTRIES = {
    "src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_diff_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_history_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_mesh_stats_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_properties_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_review_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_sync_template_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_cad_view_state_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_legacy_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py",
}


def _route_decorators(source: str) -> list[str]:
    return re.findall(r"@\w*router\.(?:get|post|delete|put|patch)\(", source)


def test_legacy_router_shells_declare_no_runtime_routes() -> None:
    for file_name in LEGACY_ROUTER_STATES:
        source = (WEB_DIR / file_name).read_text(encoding="utf-8", errors="replace")
        assert _route_decorators(source) == [], f"{file_name} still declares route handlers"


def test_legacy_router_registration_states_are_intentional() -> None:
    app_source = APP_PY.read_text(encoding="utf-8", errors="replace")

    for file_name, expected in LEGACY_ROUTER_STATES.items():
        include_token = expected["include_token"]
        import_token = expected["import_token"]
        if expected["registered"]:
            assert import_token in app_source, f"{file_name} should stay imported as a registered empty shell"
            assert include_token in app_source, f"{file_name} should stay registered as an empty shell"
        else:
            assert import_token not in app_source, f"{file_name} should not be imported by app.py"
            assert include_token not in app_source, f"{file_name} should not be registered by app.py"


def test_no_app_route_is_owned_by_legacy_router_modules() -> None:
    legacy_modules = {state["legacy_module"] for state in LEGACY_ROUTER_STATES.values()}
    leaked = sorted(
        (method, route.path, route.endpoint.__module__)
        for route in create_app().routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
        if method != "HEAD" and route.endpoint.__module__ in legacy_modules
    )

    assert leaked == []


def test_ci_contracts_job_runs_router_decomposition_portfolio_surface() -> None:
    ci_source = CI_YML.read_text(encoding="utf-8", errors="replace")
    missing = sorted(path for path in CI_PORTFOLIO_ENTRIES if path not in ci_source)

    assert missing == []
