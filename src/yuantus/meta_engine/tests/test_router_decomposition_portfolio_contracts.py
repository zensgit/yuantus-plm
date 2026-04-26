from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app


REPO_ROOT = Path(__file__).resolve().parents[4]
APP_PY = REPO_ROOT / "src" / "yuantus" / "api" / "app.py"
WEB_DIR = REPO_ROOT / "src" / "yuantus" / "meta_engine" / "web"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TESTS_DIR = REPO_ROOT / "src" / "yuantus" / "meta_engine" / "tests"

LEGACY_ROUTER_STATES = {
    "approvals_router.py": {
        "legacy_module": "yuantus.meta_engine.web.approvals_router",
        "registered": False,
        "include_token": "app.include_router(approvals_router",
        "import_token": "from yuantus.meta_engine.web.approvals_router import approvals_router",
    },
    "bom_router.py": {
        "legacy_module": "yuantus.meta_engine.web.bom_router",
        "registered": True,
        "include_token": "app.include_router(bom_router",
        "import_token": "from yuantus.meta_engine.web.bom_router import bom_router",
    },
    "box_router.py": {
        "legacy_module": "yuantus.meta_engine.web.box_router",
        "registered": True,
        "include_token": "app.include_router(box_router",
        "import_token": "from yuantus.meta_engine.web.box_router import box_router",
    },
    "cad_router.py": {
        "legacy_module": "yuantus.meta_engine.web.cad_router",
        "registered": True,
        "include_token": "app.include_router(cad_router",
        "import_token": "from yuantus.meta_engine.web.cad_router import router as cad_router",
    },
    "cutted_parts_router.py": {
        "legacy_module": "yuantus.meta_engine.web.cutted_parts_router",
        "registered": True,
        "include_token": "app.include_router(cutted_parts_router",
        "import_token": "from yuantus.meta_engine.web.cutted_parts_router import cutted_parts_router",
    },
    "document_sync_router.py": {
        "legacy_module": "yuantus.meta_engine.web.document_sync_router",
        "registered": False,
        "include_token": "app.include_router(document_sync_router",
        "import_token": "from yuantus.meta_engine.web.document_sync_router import document_sync_router",
    },
    "file_router.py": {
        "legacy_module": "yuantus.meta_engine.web.file_router",
        "registered": False,
        "include_token": "app.include_router(file_router",
        "import_token": "from yuantus.meta_engine.web.file_router import file_router",
    },
    "maintenance_router.py": {
        "legacy_module": "yuantus.meta_engine.web.maintenance_router",
        "registered": True,
        "include_token": "app.include_router(maintenance_router",
        "import_token": "from yuantus.meta_engine.web.maintenance_router import maintenance_router",
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
    "quality_router.py": {
        "legacy_module": "yuantus.meta_engine.web.quality_router",
        "registered": True,
        "include_token": "app.include_router(quality_router",
        "import_token": "from yuantus.meta_engine.web.quality_router import quality_router",
    },
    "report_router.py": {
        "legacy_module": "yuantus.meta_engine.web.report_router",
        "registered": True,
        "include_token": "app.include_router(report_router",
        "import_token": "from yuantus.meta_engine.web.report_router import report_router",
    },
    "subcontracting_router.py": {
        "legacy_module": "yuantus.meta_engine.web.subcontracting_router",
        "registered": True,
        "include_token": "app.include_router(subcontracting_router",
        "import_token": "from yuantus.meta_engine.web.subcontracting_router import subcontracting_router",
    },
    "version_router.py": {
        "legacy_module": "yuantus.meta_engine.web.version_router",
        "registered": True,
        "include_token": "app.include_router(version_router",
        "import_token": "from yuantus.meta_engine.web.version_router import version_router",
    },
}

CI_PORTFOLIO_ENTRIES = {
    "src/yuantus/meta_engine/tests/test_approval_category_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_children_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_compare_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_obsolete_rollup_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_substitutes_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_tree_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_bom_where_used_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_box_router_decomposition_closeout_contracts.py",
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
    "src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_core_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_lineage_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_retention_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_approval_ops_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_approval_workflow_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_change_analysis_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_core_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_impact_apply_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_lifecycle_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_eco_stage_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_attachment_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_metadata_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_router_shell_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_breakage_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_cad_3d_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_consumption_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_doc_sync_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_eco_activities_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_legacy_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_ops_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_workflow_actions_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_parallel_tasks_workorder_docs_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_maintenance_category_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_maintenance_equipment_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_maintenance_request_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_maintenance_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_maintenance_schedule_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_quality_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_report_dashboard_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_report_definition_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_report_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_report_summary_search_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py",
    "src/yuantus/meta_engine/tests/test_subcontracting_analytics_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_subcontracting_approval_mapping_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_subcontracting_orders_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_subcontracting_router_decomposition_closeout_contracts.py",
    "src/yuantus/meta_engine/tests/test_version_effectivity_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_version_file_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_version_iteration_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_version_lifecycle_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_version_revision_router_contracts.py",
    "src/yuantus/meta_engine/tests/test_version_router_decomposition_closeout_contracts.py",
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


def test_portfolio_entries_cover_every_router_contract_file_on_disk() -> None:
    disk_contracts = {
        str(path.relative_to(REPO_ROOT))
        for path in TESTS_DIR.glob("test_*router*_contracts.py")
    }

    assert sorted(CI_PORTFOLIO_ENTRIES) == sorted(disk_contracts)
