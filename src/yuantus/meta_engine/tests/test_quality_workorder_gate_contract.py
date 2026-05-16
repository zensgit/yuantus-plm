"""Tests for the quality ↔ workorder gate contract (R1).

Includes the four MANDATORY exactly-named tests that pin the
owner-ratified §3 policy and the §4 scope model:
- test_point_four_field_scope_wildcard_and_equality
- test_cross_scope_pass_check_does_not_clear
- test_only_production_trigger_points_gate_the_operation
- test_pass_clears_fail_warning_none_block_by_ratified_policy
plus DTO validation, an AST purity guard, and drift guards vs the real
QualityPoint/QualityCheck columns, QualityCheckResult, and the
trigger_on vocabulary.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from yuantus.meta_engine.models.item import Item  # noqa: F401 (mapper registry)
from yuantus.meta_engine.quality.models import (
    QualityCheck,
    QualityCheckResult,
    QualityPoint,
)
from yuantus.meta_engine.services import (
    quality_workorder_gate_contract as mod,
)
from yuantus.meta_engine.services.quality_workorder_gate_contract import (
    OperationQualityFacts,
    QualityCheckDescriptor,
    QualityPointDescriptor,
    assert_operation_quality_clear,
    evaluate_operation_quality_gate,
    resolve_applicable_quality_points,
)
from yuantus.meta_engine.quality.service import QualityService


def _facts(**kw):
    return OperationQualityFacts(**kw)


def _point(**kw):
    base = dict(id="pt", trigger_on="production")
    base.update(kw)
    return QualityPointDescriptor(**base)


def _check(**kw):
    base = dict(point_id="pt", result="pass")
    base.update(kw)
    return QualityCheckDescriptor(**base)


# --------------------------------------------------------------------------
# DTO validation
# --------------------------------------------------------------------------


def test_dtos_frozen_extra_forbid_and_required():
    f = _facts(product_id="p1")
    with pytest.raises(Exception):
        f.product_id = "p2"
    with pytest.raises(ValueError):
        OperationQualityFacts(bogus=1)
    with pytest.raises(ValueError, match="id must be a non-empty"):
        QualityPointDescriptor(id="  ", trigger_on="production")
    with pytest.raises(ValueError, match="point_id must be a non-empty"):
        QualityCheckDescriptor(point_id="", result="pass")


def test_check_result_validated_against_enum():
    assert _check(result="PASS").result == "pass"
    with pytest.raises(ValueError, match="result must be one of"):
        _check(result="bogus")


# --------------------------------------------------------------------------
# MANDATORY §4.1 — point four-field scope
# --------------------------------------------------------------------------


def test_point_four_field_scope_wildcard_and_equality():
    facts = _facts(
        product_id="p1", item_type_id="t1", routing_id="r1", operation_id="op1"
    )
    # all-None point = wildcard on every field -> applies
    assert resolve_applicable_quality_points(facts, [_point(id="w")])

    # each non-None field must equal facts; a mismatch on ANY of the
    # four excludes the point.
    for field, bad in (
        ("product_id", "pX"),
        ("item_type_id", "tX"),
        ("routing_id", "rX"),
        ("operation_id", "opX"),
    ):
        p = _point(id="m", **{field: bad})
        assert resolve_applicable_quality_points(facts, [p]) == (), field

    # exact match on all four -> applies
    p = _point(
        id="exact",
        product_id="p1",
        item_type_id="t1",
        routing_id="r1",
        operation_id="op1",
    )
    assert [x.id for x in resolve_applicable_quality_points(facts, [p])] == ["exact"]


# --------------------------------------------------------------------------
# MANDATORY §4.3 — per-check scope filter (cross-scope contamination)
# --------------------------------------------------------------------------


def test_cross_scope_pass_check_does_not_clear():
    facts = _facts(product_id="p1", routing_id="r1", operation_id="op1")
    point = _point(id="pt1", routing_id="r1", operation_id="op1")

    # pass check for the SAME point but a DIFFERENT scope must not clear.
    for field, bad in (
        ("product_id", "pX"),
        ("routing_id", "rX"),
        ("operation_id", "opX"),
    ):
        c = _check(point_id="pt1", result="pass", **{field: bad})
        r = evaluate_operation_quality_gate(facts, [point], [c])
        assert r.ok is False, field
        assert "pt1" in r.missing  # no scope-matching check at all

    # a pass check for a DIFFERENT point_id must not clear pt1 either.
    other = _check(point_id="OTHER", result="pass")
    r = evaluate_operation_quality_gate(facts, [point], [other])
    assert r.ok is False
    assert r.missing == ["pt1"]

    # the correctly-scoped pass DOES clear.
    good = _check(point_id="pt1", result="pass", routing_id="r1", operation_id="op1")
    assert evaluate_operation_quality_gate(facts, [point], [good]).ok is True


# --------------------------------------------------------------------------
# MANDATORY §3 — only production trigger gates
# --------------------------------------------------------------------------


def test_only_production_trigger_points_gate_the_operation():
    facts = _facts(routing_id="r1")
    for trig in ("manual", "receipt", "transfer"):
        p = _point(id=f"np-{trig}", trigger_on=trig, routing_id="r1")
        # not applicable -> empty -> ok (no gating), even with no checks
        report = evaluate_operation_quality_gate(facts, [p], [])
        assert report.total == 0
        assert report.ok is True
    # inactive production point also does not gate
    inactive = _point(id="inact", trigger_on="production", is_active=False)
    assert evaluate_operation_quality_gate(facts, [inactive], []).total == 0


# --------------------------------------------------------------------------
# MANDATORY §3 — pass clears; fail/warning/none/missing block
# --------------------------------------------------------------------------


def test_pass_clears_fail_warning_none_block_by_ratified_policy():
    # Ratified §3: ONLY "pass" clears. fail / warning / none / missing
    # all block. "warning" does NOT clear (conservative, ratified).
    facts = _facts(routing_id="r1")
    point = _point(id="pt1", routing_id="r1")

    assert evaluate_operation_quality_gate(
        facts, [point], [_check(point_id="pt1", result="pass", routing_id="r1")]
    ).ok is True

    for blocking in ("fail", "warning", "none"):
        c = _check(point_id="pt1", result=blocking, routing_id="r1")
        r = evaluate_operation_quality_gate(facts, [point], [c])
        assert r.ok is False, blocking
        assert r.blocked == ["pt1"], blocking

    # no check at all -> missing -> not ok
    r = evaluate_operation_quality_gate(facts, [point], [])
    assert r.ok is False
    assert r.missing == ["pt1"]


# --------------------------------------------------------------------------
# Gate basics + seam
# --------------------------------------------------------------------------


def test_empty_applicable_set_is_ok():
    # no production points scoped to the op => not gated => ok
    assert evaluate_operation_quality_gate(_facts(), [], []).ok is True


def test_assert_seam_raises_and_returns_none():
    facts = _facts(routing_id="r1")
    point = _point(id="pt1", routing_id="r1")
    assert (
        assert_operation_quality_clear(
            facts, [point], [_check(point_id="pt1", result="pass", routing_id="r1")]
        )
        is None
    )
    with pytest.raises(ValueError, match="operation not quality-clear"):
        assert_operation_quality_clear(facts, [point], [])


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
        "quality.service",
        "manufacturing",
        "_router",
        "plugins",
    ):
        assert forbidden not in joined, f"must stay pure: imports {forbidden!r}"
    # value domain comes from the quality model enums only
    assert "yuantus.meta_engine.quality.models" in joined


# --------------------------------------------------------------------------
# Drift guards vs real model / enum / vocabulary
# --------------------------------------------------------------------------


def test_drift_point_descriptor_fields_subset_of_quality_point_columns():
    cols = {c.name for c in QualityPoint.__table__.columns}
    fields = set(QualityPointDescriptor.model_fields.keys())
    missing = fields - cols
    assert not missing, f"point descriptor fields not on QualityPoint: {missing}"


def test_drift_check_descriptor_fields_subset_of_quality_check_columns():
    cols = {c.name for c in QualityCheck.__table__.columns}
    fields = set(QualityCheckDescriptor.model_fields.keys())
    missing = fields - cols
    # in particular this fails loudly if item_type_id is wrongly added
    # to the check descriptor (QualityCheck has no such column).
    assert not missing, f"check descriptor fields not on QualityCheck: {missing}"
    assert "item_type_id" not in cols  # honest asymmetry, pinned


def test_drift_result_domain_matches_enum():
    assert set(mod._RESULT_VALUES) == {r.value for r in QualityCheckResult}
    assert mod._CLEARING_RESULT == "pass"


def test_drift_production_trigger_in_quality_service_vocabulary():
    # Source-level guard: if QualityService.create_point drops/renames
    # the "production" trigger, this contract silently stops gating —
    # fail loudly here instead.
    src = inspect.getsource(QualityService.create_point)
    assert "trigger_on not in" in src
    assert '"production"' in src
    assert mod._PRODUCTION_TRIGGER == "production"
