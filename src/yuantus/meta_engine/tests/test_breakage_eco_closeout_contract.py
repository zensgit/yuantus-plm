"""Tests for the breakage → ECO closeout contract (R1).

Includes the two MANDATORY exactly-named tests that pin the
owner-ratified policies (taskbook §3):
- test_resolved_and_closed_are_eligible_only
- test_unknown_severity_maps_to_normal_by_ratified_policy
plus mapping/bom-edge, not-eligible, reference determinism, an AST
purity guard, and drift guards vs the real BreakageIncident columns,
the breakage status vocabulary, and ECOPriority.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from yuantus.meta_engine.models.eco import ECOPriority
from yuantus.meta_engine.models.parallel_tasks import BreakageIncident
from yuantus.meta_engine.services import (
    breakage_eco_closeout_contract as mod,
)
from yuantus.meta_engine.services.breakage_eco_closeout_contract import (
    BreakageEcoClosureDescriptor,
    derive_breakage_change_reference,
    eligible_statuses,
    is_breakage_eligible_for_design_loopback,
    map_breakage_to_change_request_intake,
    severity_priority,
    severity_to_priority,
)
from yuantus.meta_engine.services.ecr_intake_contract import (
    ChangeRequestIntake,
    map_change_request_to_eco_draft_inputs,
)
from yuantus.meta_engine.services.parallel_tasks_service import (
    BreakageIncidentService,
)


def _d(**kw):
    base = dict(description="cracked under load", status="resolved")
    base.update(kw)
    return BreakageEcoClosureDescriptor(**base)


# --------------------------------------------------------------------------
# Descriptor validation
# --------------------------------------------------------------------------


def test_descriptor_frozen_extra_forbid_and_required():
    d = _d()
    with pytest.raises(Exception):
        d.status = "closed"
    with pytest.raises(ValueError):
        BreakageEcoClosureDescriptor(description="d", status="resolved", bogus=1)
    with pytest.raises(ValueError, match="description must be a non-empty"):
        BreakageEcoClosureDescriptor(description="   ", status="resolved")


def test_descriptor_normalizes_status_severity_and_blanks():
    d = BreakageEcoClosureDescriptor(
        description="d",
        status="  RESOLVED ",
        severity="  HIGH ",
        incident_code="  ",
        product_item_id=" p1 ",
    )
    assert d.status == "resolved"
    assert d.severity == "high"
    assert d.incident_code is None
    assert d.product_item_id == "p1"


# --------------------------------------------------------------------------
# RATIFIED policy §3.1 — MANDATORY exactly-named test
# --------------------------------------------------------------------------


def test_resolved_and_closed_are_eligible_only():
    # Ratified §3.1: eligible_statuses == {"resolved", "closed"}.
    # open / in_progress / any unknown status are NOT eligible.
    assert eligible_statuses == frozenset({"resolved", "closed"})
    assert is_breakage_eligible_for_design_loopback(_d(status="resolved")) is True
    assert is_breakage_eligible_for_design_loopback(_d(status="closed")) is True
    assert is_breakage_eligible_for_design_loopback(_d(status="CLOSED")) is True
    for not_eligible in ("open", "in_progress", "canceled", "weird", "done"):
        assert (
            is_breakage_eligible_for_design_loopback(_d(status=not_eligible))
            is False
        ), not_eligible


# --------------------------------------------------------------------------
# RATIFIED policy §3.2 — MANDATORY exactly-named test
# --------------------------------------------------------------------------


def test_unknown_severity_maps_to_normal_by_ratified_policy():
    # Ratified §3.2: pinned table, and ANY unrecognized severity maps to
    # "normal" — a documented conservative *downgrade* policy, NOT a
    # silent fallback.
    assert severity_to_priority == {
        "critical": "urgent",
        "high": "high",
        "medium": "normal",
        "low": "low",
    }
    assert severity_priority("critical") == "urgent"
    assert severity_priority("high") == "high"
    assert severity_priority("medium") == "normal"
    assert severity_priority("low") == "low"
    assert severity_priority("CRITICAL") == "urgent"  # case-insensitive
    # unknown / dirty severity -> normal (conservative downgrade)
    for unknown in ("blocker", "sev1", "", "  ", "catastrophic", "p0"):
        assert severity_priority(unknown) == "normal", unknown


# --------------------------------------------------------------------------
# Mapping (composes with the shipped ECR intake contract)
# --------------------------------------------------------------------------


def test_map_bom_with_product_id_is_bom_type():
    intake = map_breakage_to_change_request_intake(
        _d(status="resolved", bom_id="b1", product_item_id="p1", severity="high")
    )
    assert isinstance(intake, ChangeRequestIntake)
    assert intake.change_type == "bom"
    assert intake.product_id == "p1"
    assert intake.priority == "high"


def test_map_bom_without_product_id_falls_back_to_product_type():
    # bom ⇒ product_id invariant of ChangeRequestIntake: a bom_id with
    # no product_item_id must NOT claim change_type="bom" (that would
    # raise inside ChangeRequestIntake).
    intake = map_breakage_to_change_request_intake(
        _d(status="closed", bom_id="b1", product_item_id=None, severity="critical")
    )
    assert intake.change_type == "product"
    assert intake.product_id is None
    assert intake.priority == "urgent"


def test_map_no_bom_is_product_type_and_envelope_present():
    intake = map_breakage_to_change_request_intake(
        _d(status="resolved", incident_code="BRK-9", product_item_id="p9")
    )
    assert intake.change_type == "product"
    assert intake.title == "Design loopback: BRK-9"
    assert intake.reason.startswith("cracked under load")
    assert "breakage-eco-closeout" in intake.reason
    assert derive_breakage_change_reference(
        _d(status="resolved", incident_code="BRK-9", product_item_id="p9")
    ) in intake.reason


def test_map_output_composes_through_ecr_contract_without_db():
    intake = map_breakage_to_change_request_intake(
        _d(status="resolved", bom_id="b1", product_item_id="p1")
    )
    # Proves shape-compatibility with the shipped ECR contract; no DB.
    eco_kwargs = map_change_request_to_eco_draft_inputs(intake).as_kwargs()
    assert eco_kwargs["eco_type"] == "bom"
    assert eco_kwargs["product_id"] == "p1"


def test_map_not_eligible_raises():
    with pytest.raises(ValueError, match="not eligible for design loopback"):
        map_breakage_to_change_request_intake(_d(status="open"))


# --------------------------------------------------------------------------
# Reference
# --------------------------------------------------------------------------


def test_reference_deterministic_and_per_field():
    a = _d(status="resolved", incident_code="C", product_item_id="p", version_id="v")
    b = _d(status="closed", incident_code="C", product_item_id="p", version_id="v")
    # description/status do not feed the reference; identity fields do.
    assert derive_breakage_change_reference(a) == derive_breakage_change_reference(b)
    other = _d(status="resolved", incident_code="C2", product_item_id="p", version_id="v")
    assert derive_breakage_change_reference(a) != derive_breakage_change_reference(other)
    ref = derive_breakage_change_reference(a)
    assert len(ref) == 64
    int(ref, 16)


# --------------------------------------------------------------------------
# Purity guard
# --------------------------------------------------------------------------


def test_module_is_pure():
    tree = ast.parse(inspect.getsource(mod))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    joined = " ".join(imported)
    for forbidden in (
        "yuantus.database",
        "sqlalchemy",
        "parallel_tasks_service",
        "_router",
        "plugins",
    ):
        assert forbidden not in joined, f"must stay pure: imports {forbidden!r}"
    # reuses the shipped ECR intake contract as a pure dependency
    assert "yuantus.meta_engine.services.ecr_intake_contract" in joined


# --------------------------------------------------------------------------
# Drift guards vs the real model / vocabulary / enum
# --------------------------------------------------------------------------


def test_drift_descriptor_fields_subset_of_breakage_columns():
    columns = {c.name for c in BreakageIncident.__table__.columns}
    fields = set(BreakageEcoClosureDescriptor.model_fields.keys())
    missing = fields - columns
    assert not missing, f"descriptor fields not on BreakageIncident: {missing}"


def test_drift_eligible_statuses_within_breakage_vocabulary():
    # Subset (not equality): the exact ratified set is pinned by
    # test_resolved_and_closed_are_eligible_only; this guard only
    # ensures we never reference a status the breakage domain cannot
    # produce.
    vocab = set(
        BreakageIncidentService._HELPDESK_PROVIDER_TO_INCIDENT_STATUS.values()
    )
    assert eligible_statuses <= vocab, (
        f"eligible_statuses {set(eligible_statuses)} not a subset of "
        f"breakage status vocabulary {vocab}"
    )


def test_drift_severity_priority_codomain_subset_of_eco_priority():
    eco_priorities = {p.value for p in ECOPriority}
    # Pin the ratified §3.2 unknown-fallback value explicitly so it
    # cannot silently drift to another (still-valid) ECOPriority.
    assert mod._UNKNOWN_SEVERITY_PRIORITY == "normal"  # ratified §3.2
    assert mod._UNKNOWN_SEVERITY_PRIORITY in eco_priorities
    codomain = set(severity_to_priority.values()) | {
        mod._UNKNOWN_SEVERITY_PRIORITY
    }
    assert codomain <= eco_priorities, (
        f"severity_to_priority codomain {codomain} not a subset of "
        f"ECOPriority {eco_priorities}"
    )
