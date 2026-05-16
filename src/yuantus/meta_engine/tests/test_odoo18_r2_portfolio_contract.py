"""Odoo18 R2 portfolio drift guard (read-only, pure introspection).

Anti-memory-drift: asserts the 7 standalone pure-contract modules and
their documented public symbols still exist, that the non-module
workorder version-lock surface (#565) still exists, and that the R2
closeout MD stays consistent with the codebase (lists all 8 impl PRs;
every services/*_contract.py path it cites is real). No runtime.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from yuantus.meta_engine.models.item import Item  # noqa: F401 (mapper registry)

_CLOSEOUT = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "DEV_AND_VERIFICATION_ODOO18_R2_PORTFOLIO_CLOSEOUT_20260516.md"
)

# The 7 standalone pure-contract modules + their documented key public
# symbols. A rename/removal of any of these fails loudly here.
_PURE_CONTRACTS = {
    "yuantus.meta_engine.services.consumption_mes_contract": (
        "MesConsumptionEvent",
        "ConsumptionRecordInputs",
        "derive_consumption_idempotency_key",
        "map_mes_event_to_consumption_record_inputs",
    ),
    "yuantus.meta_engine.services.pack_and_go_version_lock_contract": (
        "BundleDocumentDescriptor",
        "BundleLockReport",
        "evaluate_bundle_version_locks",
        "assert_bundle_version_locks",
    ),
    "yuantus.meta_engine.services.maintenance_workorder_bridge_contract": (
        "WorkcenterMaintenanceDescriptor",
        "WorkcenterReadinessReport",
        "evaluate_workcenter_readiness",
        "assert_workcenter_ready",
    ),
    "yuantus.meta_engine.services.ecr_intake_contract": (
        "ChangeRequestIntake",
        "EcoDraftInputs",
        "derive_change_request_reference",
        "map_change_request_to_eco_draft_inputs",
    ),
    "yuantus.meta_engine.services.automation_rule_predicate_contract": (
        "WorkflowRulePredicate",
        "WorkflowRuleFacts",
        "normalize_workflow_rule_predicate",
        "evaluate_rule_predicate",
    ),
    "yuantus.meta_engine.services.breakage_eco_closeout_contract": (
        "BreakageEcoClosureDescriptor",
        "is_breakage_eligible_for_design_loopback",
        "severity_priority",
        "derive_breakage_change_reference",
        "map_breakage_to_change_request_intake",
    ),
    "yuantus.meta_engine.services.quality_workorder_gate_contract": (
        "OperationQualityFacts",
        "QualityPointDescriptor",
        "QualityCheckDescriptor",
        "OperationQualityGateReport",
        "resolve_applicable_quality_points",
        "evaluate_operation_quality_gate",
        "assert_operation_quality_clear",
    ),
}

_IMPL_PRS = (565, 567, 570, 572, 574, 577, 579, 581)


@pytest.mark.parametrize("module_path,symbols", list(_PURE_CONTRACTS.items()))
def test_pure_contract_module_exposes_documented_symbols(module_path, symbols):
    mod = importlib.import_module(module_path)
    missing = [s for s in symbols if not hasattr(mod, s)]
    assert not missing, f"{module_path} lost public symbols: {missing}"


def test_workorder_version_lock_surface_still_exists():
    # #565 is a service extension, not a standalone module — assert its
    # real surface so the portfolio record stays honest about it.
    from yuantus.meta_engine.services.parallel_tasks_service import (
        WorkorderDocumentPackService,
    )
    from yuantus.meta_engine.web.parallel_tasks_workorder_docs_router import (
        parallel_tasks_workorder_docs_router,
    )
    from yuantus.meta_engine.models.parallel_tasks import WorkorderDocumentLink

    for attr in ("upsert_link", "serialize_link", "export_pack"):
        assert hasattr(WorkorderDocumentPackService, attr), attr
    cols = {c.name for c in WorkorderDocumentLink.__table__.columns}
    assert {
        "document_version_id",
        "version_locked_at",
        "version_lock_source",
    } <= cols
    assert parallel_tasks_workorder_docs_router is not None


def test_closeout_md_exists_and_lists_all_eight_impl_prs():
    assert _CLOSEOUT.exists(), f"closeout MD missing: {_CLOSEOUT}"
    text = _CLOSEOUT.read_text()
    for pr in _IMPL_PRS:
        assert f"#{pr}" in text, f"closeout MD does not list impl PR #{pr}"


def test_closeout_md_cited_module_paths_exist_on_disk():
    text = _CLOSEOUT.read_text()
    repo = Path(__file__).resolve().parents[4]
    cited = set(re.findall(r"services/([a-z_]+_contract)\.py", text))
    # every standalone pure-contract module named in _PURE_CONTRACTS
    # must be cited by the closeout AND exist on disk.
    for module_path in _PURE_CONTRACTS:
        name = module_path.rsplit(".", 1)[1]
        assert name in cited, f"closeout MD does not cite {name}.py"
        assert (
            repo / "src" / "yuantus" / "meta_engine" / "services" / f"{name}.py"
        ).exists(), f"cited module {name}.py missing on disk"
