"""Tests for the ECR dedupe pure-contract (R1, REPORT ONLY).

Covers empty/all-distinct/2-way/3-way reports, deterministic ordering,
a composition/drift guard pinning the shipped reference function, the
no-enforcement guard (no `assert_*`, no `raise`), and a purity guard.
"""

from __future__ import annotations

import ast
import inspect

from yuantus.meta_engine.services import ecr_dedupe_contract as mod
from yuantus.meta_engine.services.ecr_dedupe_contract import (
    ChangeRequestDedupeReport,
    ChangeRequestReferenceCollision,
    build_change_request_dedupe_report,
)
from yuantus.meta_engine.services.ecr_intake_contract import (
    ChangeRequestIntake,
    derive_change_request_reference,
)


def _intake(title="Fix", change_type="product", product_id="p1",
            requester_user_id=7, reason=None, priority="normal"):
    return ChangeRequestIntake(
        title=title,
        change_type=change_type,
        product_id=product_id,
        requester_user_id=requester_user_id,
        reason=reason,
        priority=priority,
    )


# --------------------------------------------------------------------------
# Report shape
# --------------------------------------------------------------------------


def test_empty_input():
    r = build_change_request_dedupe_report([])
    assert r == ChangeRequestDedupeReport(
        total=0, unique_references=0, collisions=(), has_collisions=False
    )


def test_all_distinct_no_collisions():
    items = [
        ("k1", _intake(title="A")),
        ("k2", _intake(title="B")),
        ("k3", _intake(title="C")),
    ]
    r = build_change_request_dedupe_report(items)
    assert r.total == 3
    assert r.unique_references == 3
    assert r.collisions == ()
    assert r.has_collisions is False


def test_two_way_collision_ignores_non_reference_fields():
    # reason / priority / effectivity_date are NOT part of the
    # reference, so these two collide.
    a = _intake(reason="r1", priority="high")
    b = _intake(reason="totally different", priority="low")
    c = _intake(title="Unrelated")
    r = build_change_request_dedupe_report([("k1", a), ("k2", b), ("k3", c)])
    assert r.total == 3
    assert r.unique_references == 2
    assert r.has_collisions is True
    assert len(r.collisions) == 1
    col = r.collisions[0]
    assert isinstance(col, ChangeRequestReferenceCollision)
    assert col.reference == derive_change_request_reference(a)
    assert col.keys == ("k1", "k2")  # input order preserved


def test_three_way_collision_plus_unique():
    items = [
        ("a", _intake()),
        ("b", _intake()),
        ("c", _intake()),
        ("z", _intake(title="Z")),
    ]
    r = build_change_request_dedupe_report(items)
    assert r.total == 4
    assert r.unique_references == 2
    assert len(r.collisions) == 1
    assert r.collisions[0].keys == ("a", "b", "c")


def test_collisions_sorted_by_reference_and_keys_input_order():
    # Two independent collision groups; assert deterministic ordering.
    g1a, g1b = _intake(title="G1"), _intake(title="G1")
    g2a, g2b = _intake(title="G2"), _intake(title="G2")
    items = [
        ("g2-second", g2b),
        ("g1-second", g1b),
        ("g1-first", g1a),
        ("g2-first", g2a),
    ]
    r = build_change_request_dedupe_report(items)
    refs = [c.reference for c in r.collisions]
    assert refs == sorted(refs)
    by_ref = {c.reference: c.keys for c in r.collisions}
    # within each group, keys follow input order
    assert by_ref[derive_change_request_reference(g1a)] == ("g1-second", "g1-first")
    assert by_ref[derive_change_request_reference(g2a)] == ("g2-second", "g2-first")


def test_function_is_pure_same_input_same_report():
    items = [("k1", _intake(reason="x")), ("k2", _intake(reason="y"))]
    assert build_change_request_dedupe_report(items) == (
        build_change_request_dedupe_report(items)
    )


def test_duplicate_caller_keys_are_grouped_not_validated():
    # The caller owns key semantics; the contract only groups by
    # reference and does not reject duplicate keys.
    r = build_change_request_dedupe_report(
        [("dup", _intake()), ("dup", _intake())]
    )
    assert r.collisions[0].keys == ("dup", "dup")


# --------------------------------------------------------------------------
# Composition / drift guard (reference reused, not reimplemented)
# --------------------------------------------------------------------------


def test_report_reference_equals_shipped_derivation():
    a = _intake(title="Compose", product_id="pX", requester_user_id=3)
    b = _intake(title="Compose", product_id="pX", requester_user_id=3, reason="z")
    r = build_change_request_dedupe_report([("a", a), ("b", b)])
    assert r.collisions[0].reference == derive_change_request_reference(a)
    assert r.collisions[0].reference == derive_change_request_reference(b)


# --------------------------------------------------------------------------
# No-enforcement guard (REPORT ONLY)
# --------------------------------------------------------------------------


def test_module_has_no_enforcement():
    tree = ast.parse(inspect.getsource(mod))
    # no callable named assert_*
    assert_fns = [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("assert_")
    ]
    assert not assert_fns, f"report-only module must not enforce: {assert_fns}"
    # report-only: the module raises nothing at all
    raises = [n for n in ast.walk(tree) if isinstance(n, ast.Raise)]
    assert not raises, "report-only module must not raise"


# --------------------------------------------------------------------------
# Purity guard
# --------------------------------------------------------------------------


def test_module_is_pure_imports_only_ecr_intake_contract():
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
        "_service",
        "_router",
        "plugins",
    ):
        assert forbidden not in joined, f"must stay pure: imports {forbidden!r}"
    assert "yuantus.meta_engine.services.ecr_intake_contract" in joined
