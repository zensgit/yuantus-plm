"""Tests for the maintenance ↔ workorder bridge contract (R1).

Pure-contract coverage: descriptor validation incl. unknown-enum
fail-fast, the blocked/degraded rule, the deliberate `draft`
non-blocking divergence from get_maintenance_queue_summary, multi-
workcenter grouping/order, the report/raise split incl.
absent-workcenter-not-vacuously-ready, a purity guard, and an enum
drift guard introspecting the real maintenance enums.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from yuantus.meta_engine.maintenance.models import (
    EquipmentStatus,
    MaintenanceRequestState,
)
from yuantus.meta_engine.services import (
    maintenance_workorder_bridge_contract as mod,
)
from yuantus.meta_engine.services.maintenance_workorder_bridge_contract import (
    WorkcenterMaintenanceDescriptor,
    WorkcenterReadinessReport,
    assert_workcenter_ready,
    evaluate_workcenter_readiness,
)


def _d(wc, eq, status="operational", req=None):
    return WorkcenterMaintenanceDescriptor(
        workcenter_id=wc,
        equipment_id=eq,
        equipment_status=status,
        active_request_state=req,
    )


# --------------------------------------------------------------------------
# Descriptor validation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["workcenter_id", "equipment_id"])
def test_descriptor_rejects_empty_ids(field):
    kwargs = dict(
        workcenter_id="wc", equipment_id="eq", equipment_status="operational"
    )
    kwargs[field] = "   "
    with pytest.raises(ValueError, match="non-empty"):
        WorkcenterMaintenanceDescriptor(**kwargs)


def test_descriptor_strips_ids():
    d = _d("  wc1  ", "  e1  ")
    assert d.workcenter_id == "wc1"
    assert d.equipment_id == "e1"


def test_descriptor_rejects_unknown_equipment_status():
    with pytest.raises(ValueError, match="equipment_status must be one of"):
        _d("wc", "e", status="exploded")


def test_descriptor_rejects_unknown_request_state():
    with pytest.raises(ValueError, match="active_request_state must be one of"):
        _d("wc", "e", req="pending")


def test_descriptor_accepts_none_request_state():
    assert _d("wc", "e", req=None).active_request_state is None


def test_descriptor_is_frozen_and_forbids_extra():
    d = _d("wc", "e")
    with pytest.raises(Exception):
        d.equipment_status = "out_of_service"
    with pytest.raises(ValueError):
        WorkcenterMaintenanceDescriptor(
            workcenter_id="wc",
            equipment_id="e",
            equipment_status="operational",
            bogus=1,
        )


# --------------------------------------------------------------------------
# Blocked / degraded rule
# --------------------------------------------------------------------------


def test_all_operational_is_ready():
    r = evaluate_workcenter_readiness([_d("wc", "e1"), _d("wc", "e2")])
    assert len(r) == 1
    assert r[0].ready is True
    assert r[0].total_equipment == 2
    assert r[0].blocked == []
    assert r[0].degraded == []


@pytest.mark.parametrize("status", ["out_of_service", "decommissioned"])
def test_bad_equipment_status_blocks(status):
    r = evaluate_workcenter_readiness([_d("wc", "e1", status=status)])
    assert r[0].blocked == ["e1"]
    assert r[0].ready is False


@pytest.mark.parametrize("state", ["submitted", "in_progress"])
def test_active_request_blocks_even_if_operational(state):
    r = evaluate_workcenter_readiness(
        [_d("wc", "e1", status="operational", req=state)]
    )
    assert r[0].blocked == ["e1"]
    assert r[0].ready is False


@pytest.mark.parametrize("state", ["done", "cancelled"])
def test_closed_request_does_not_block(state):
    r = evaluate_workcenter_readiness(
        [_d("wc", "e1", status="operational", req=state)]
    )
    assert r[0].blocked == []
    assert r[0].ready is True


def test_draft_request_does_not_block_readiness():
    # DELIBERATE DIVERGENCE: MaintenanceService.get_maintenance_queue_summary
    # counts `draft` into the active maintenance queue. This contract
    # answers a different question ("is the workcenter blocked right
    # now?") and a draft request is not yet active, so it must NOT block
    # readiness. Do not "fix" this into agreement with the queue summary.
    r = evaluate_workcenter_readiness(
        [_d("wc", "e1", status="operational", req="draft")]
    )
    assert r[0].blocked == []
    assert r[0].degraded == []
    assert r[0].ready is True


def test_in_maintenance_is_degraded_but_still_ready():
    r = evaluate_workcenter_readiness(
        [_d("wc", "e1", status="in_maintenance")]
    )
    assert r[0].degraded == ["e1"]
    assert r[0].blocked == []
    assert r[0].ready is True  # degraded never fails ready


def test_in_maintenance_with_blocking_request_is_blocked_not_degraded():
    r = evaluate_workcenter_readiness(
        [_d("wc", "e1", status="in_maintenance", req="in_progress")]
    )
    assert r[0].blocked == ["e1"]
    assert r[0].degraded == []
    assert r[0].ready is False


# --------------------------------------------------------------------------
# Multi-workcenter grouping & ordering
# --------------------------------------------------------------------------


def test_multiple_workcenters_one_report_each_sorted():
    ds = [
        _d("wc-b", "e1"),
        _d("wc-a", "e2", status="out_of_service"),
        _d("wc-b", "e3", status="in_maintenance"),
        _d("wc-a", "e4"),
    ]
    reports = evaluate_workcenter_readiness(ds)
    assert [r.workcenter_id for r in reports] == ["wc-a", "wc-b"]  # sorted
    by_wc = {r.workcenter_id: r for r in reports}
    assert by_wc["wc-a"].total_equipment == 2
    assert by_wc["wc-a"].blocked == ["e2"]
    assert by_wc["wc-a"].ready is False
    assert by_wc["wc-b"].total_equipment == 2
    assert by_wc["wc-b"].degraded == ["e3"]
    assert by_wc["wc-b"].ready is True


def test_empty_descriptors_yield_no_reports():
    assert evaluate_workcenter_readiness([]) == []


# --------------------------------------------------------------------------
# Report / raise split
# --------------------------------------------------------------------------


def test_evaluate_never_raises_and_takes_no_flag():
    sig = inspect.signature(evaluate_workcenter_readiness)
    assert [p for p in sig.parameters] == ["descriptors"]
    out = evaluate_workcenter_readiness([_d("wc", "e", status="out_of_service")])
    assert isinstance(out[0], WorkcenterReadinessReport)
    assert out[0].ready is False


def test_assert_returns_none_when_ready():
    assert (
        assert_workcenter_ready([_d("wc", "e1")], workcenter_id="wc") is None
    )


def test_assert_raises_listing_blocked_ids():
    with pytest.raises(ValueError, match="workcenter_blocked:"):
        assert_workcenter_ready(
            [_d("wc", "e1", status="out_of_service")], workcenter_id="wc"
        )


def test_assert_absent_workcenter_is_not_vacuously_ready():
    with pytest.raises(ValueError, match="workcenter_unknown:"):
        assert_workcenter_ready([_d("wc", "e1")], workcenter_id="other")


def test_assert_rejects_blank_workcenter_id_argument():
    with pytest.raises(ValueError, match="workcenter_invalid:"):
        assert_workcenter_ready([_d("wc", "e1")], workcenter_id="   ")


def test_assert_failure_prefixes_are_distinct_discriminators():
    # A caller must be able to tell transient-blocked from
    # not-transient-unknown from caller-bug-invalid without catching
    # ValueError blindly.
    seen = set()
    for ds, wc in (
        ([_d("wc", "e1")], "   "),  # invalid
        ([_d("wc", "e1", status="out_of_service")], "wc"),  # blocked
        ([_d("wc", "e1")], "absent"),  # unknown
    ):
        try:
            assert_workcenter_ready(ds, workcenter_id=wc)
        except ValueError as exc:
            seen.add(str(exc).split(":", 1)[0])
    assert seen == {
        "workcenter_invalid",
        "workcenter_blocked",
        "workcenter_unknown",
    }


def test_assert_does_not_raise_on_degraded_only():
    assert (
        assert_workcenter_ready(
            [_d("wc", "e1", status="in_maintenance")], workcenter_id="wc"
        )
        is None
    )


# --------------------------------------------------------------------------
# Purity guard
# --------------------------------------------------------------------------


def test_module_has_no_forbidden_imports():
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
        "maintenance.service",
        "_router",
        "plugins",
    ):
        assert forbidden not in joined, (
            f"contract must stay pure: imports {forbidden!r}"
        )
    # It MAY (and must, for the drift guard) import the maintenance enums.
    assert "yuantus.meta_engine.maintenance.models" in joined


def test_evaluate_has_no_db_parameter():
    sig = inspect.signature(evaluate_workcenter_readiness)
    assert set(sig.parameters) == {"descriptors"}


# --------------------------------------------------------------------------
# Enum drift guard vs the real maintenance enums
# --------------------------------------------------------------------------


def test_equipment_status_domain_tracks_real_enum():
    accepted = set(mod._EQUIPMENT_STATUS_VALUES)
    real = {s.value for s in EquipmentStatus}
    assert accepted == real, (
        "equipment_status domain drifted from EquipmentStatus; "
        f"missing={real - accepted} extra={accepted - real}"
    )


def test_request_state_domain_tracks_real_enum():
    accepted = set(mod._REQUEST_STATE_VALUES)
    real = {s.value for s in MaintenanceRequestState}
    assert accepted == real, (
        "active_request_state domain drifted from MaintenanceRequestState; "
        f"missing={real - accepted} extra={accepted - real}"
    )


def test_blocking_sets_are_subsets_of_real_enums():
    assert mod._BLOCKING_EQUIPMENT_STATUSES <= {
        s.value for s in EquipmentStatus
    }
    assert mod._BLOCKING_REQUEST_STATES <= {
        s.value for s in MaintenanceRequestState
    }
    # draft must NOT be a blocking request state (the divergence pin).
    assert MaintenanceRequestState.DRAFT.value not in mod._BLOCKING_REQUEST_STATES
