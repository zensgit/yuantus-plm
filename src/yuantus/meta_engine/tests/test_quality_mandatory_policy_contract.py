"""Tests for the quality is_mandatory policy overlay (R1, REPORT ONLY).

Includes the three MANDATORY exactly-named boundary tests:
- test_default_is_mandatory_preserves_shipped_gate_behavior
- test_is_mandatory_is_descriptor_only_no_schema_no_runtime
- test_shipped_gate_contract_is_untouched
plus policy/classification behavior and an AST no-enforcement/purity
guard.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from yuantus.meta_engine.models.item import Item  # noqa: F401 (mapper registry)
from yuantus.meta_engine.quality.models import QualityPoint
from yuantus.meta_engine.services import (
    quality_mandatory_policy_contract as mod,
)
from yuantus.meta_engine.services.quality_mandatory_policy_contract import (
    MandatoryGateReport,
    MandatoryPolicy,
    classify_gate_result_by_mandatory,
)
from yuantus.meta_engine.services.quality_workorder_gate_contract import (
    OperationQualityGateReport,
    QualityPointDescriptor,
)


def _report(cleared=(), blocked=(), missing=(), ok=None):
    if ok is None:
        ok = not blocked and not missing
    return OperationQualityGateReport(
        total=len(cleared) + len(blocked) + len(missing),
        cleared=list(cleared),
        blocked=list(blocked),
        missing=list(missing),
        ok=ok,
    )


# --------------------------------------------------------------------------
# MandatoryPolicy
# --------------------------------------------------------------------------


def test_policy_frozen_default_true_explicit_false():
    p = MandatoryPolicy.from_mapping({"a": False, "b": True})
    assert p.is_mandatory("a") is False  # explicit False honoured
    assert p.is_mandatory("b") is True  # explicit True == default
    assert p.is_mandatory("missing") is True  # default mandatory
    with pytest.raises(Exception):
        p._non_mandatory = frozenset()  # frozen
    assert MandatoryPolicy.empty().is_mandatory("anything") is True


# --------------------------------------------------------------------------
# Classification behavior
# --------------------------------------------------------------------------


def test_blocked_point_without_policy_is_mandatory_blocked():
    r = classify_gate_result_by_mandatory(
        _report(blocked=["b1"]), MandatoryPolicy.empty()
    )
    assert r.mandatory_blocked == ("b1",)
    assert r.advisory_unmet == ()
    assert r.mandatory_ok is False


def test_non_mandatory_point_is_advisory_not_blocking():
    r = classify_gate_result_by_mandatory(
        _report(blocked=["b1"], missing=["m1"]),
        MandatoryPolicy.from_mapping({"b1": False}),
    )
    assert r.mandatory_blocked == ("m1",)
    assert r.advisory_unmet == ("b1",)
    assert r.mandatory_ok is False


def test_all_unmet_advisory_makes_mandatory_ok_true():
    r = classify_gate_result_by_mandatory(
        _report(blocked=["b1"], missing=["m1"]),
        MandatoryPolicy.from_mapping({"b1": False, "m1": False}),
    )
    assert r.mandatory_blocked == ()
    assert r.advisory_unmet == ("b1", "m1")
    assert r.mandatory_ok is True  # advisory never fails


def test_cleared_is_passthrough():
    r = classify_gate_result_by_mandatory(
        _report(cleared=["c1", "c2"], blocked=["b1"]),
        MandatoryPolicy.empty(),
    )
    assert r.cleared == ("c1", "c2")


# --------------------------------------------------------------------------
# MANDATORY — default preserves shipped gate behavior
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rep",
    [
        _report(cleared=["c1"]),  # ok
        _report(blocked=["b1"]),  # not ok
        _report(missing=["m1"]),  # not ok
        _report(cleared=["c1"], blocked=["b1"], missing=["m1"]),  # mixed
    ],
)
def test_default_is_mandatory_preserves_shipped_gate_behavior(rep):
    # Empty policy: every blocked/missing point is mandatory_blocked,
    # and mandatory_ok == the shipped report's ok. No policy ⇒ verdict
    # identical to the shipped gate (taskbook §3.2 pinned).
    r = classify_gate_result_by_mandatory(rep, MandatoryPolicy.empty())
    assert set(r.mandatory_blocked) == set(rep.blocked) | set(rep.missing)
    assert r.advisory_unmet == ()
    assert r.mandatory_ok == rep.ok


# --------------------------------------------------------------------------
# MANDATORY — descriptor-only, no schema, no runtime
# --------------------------------------------------------------------------


def test_is_mandatory_is_descriptor_only_no_schema_no_runtime():
    # (a) QualityPoint has no is_mandatory column.
    cols = {c.name for c in QualityPoint.__table__.columns}
    assert "is_mandatory" not in cols

    # (b) shipped QualityPointDescriptor is unchanged (no is_mandatory),
    # so #581's column-subset drift guard is unaffected.
    assert "is_mandatory" not in set(QualityPointDescriptor.model_fields)

    # (c) the new module: no DB/sqlalchemy/router/_service import, no
    # raise, and it does NOT call evaluate_operation_quality_gate.
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
        "_router",
        "plugins",
        "_service",
    ):
        assert forbidden not in joined, f"impure import: {forbidden!r}"
    # type-only reuse of the shipped gate module is allowed; calling it
    # is not.
    assert "quality_workorder_gate_contract" in joined
    assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree)), (
        "report-only module must not raise"
    )
    called = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    } | {
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "evaluate_operation_quality_gate" not in called


def test_no_assert_callable_in_module():
    tree = ast.parse(inspect.getsource(mod))
    assert not [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("assert_")
    ]


# --------------------------------------------------------------------------
# MANDATORY — shipped gate contract untouched
# --------------------------------------------------------------------------


def test_shipped_gate_contract_is_untouched():
    # QualityPointDescriptor field set is exactly the merged #581 set.
    assert set(QualityPointDescriptor.model_fields) == {
        "id",
        "is_active",
        "item_type_id",
        "operation_id",
        "product_id",
        "routing_id",
        "trigger_on",
    }
    # the four MANDATORY shipped-gate tests still exist verbatim.
    gate_test = (
        Path(__file__).resolve().parent
        / "test_quality_workorder_gate_contract.py"
    ).read_text()
    for name in (
        "test_point_four_field_scope_wildcard_and_equality",
        "test_cross_scope_pass_check_does_not_clear",
        "test_only_production_trigger_points_gate_the_operation",
        "test_pass_clears_fail_warning_none_block_by_ratified_policy",
    ):
        assert f"def {name}(" in gate_test, name
