"""Tests for the pack-and-go version-lock bridge contract (R1).

Pure-contract coverage: descriptor validation, classification,
`locked` arithmetic pinned to R1, stale-never-fails-the-gate, the
report/raise split, a purity guard, and a drift guard that introspects
R1 `WorkorderDocumentPackService.serialize_link` so a rename there fails
loudly here.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.services import pack_and_go_version_lock_contract as mod
from yuantus.meta_engine.services.pack_and_go_version_lock_contract import (
    BundleDocumentDescriptor,
    BundleLockReport,
    assert_bundle_version_locks,
    evaluate_bundle_version_locks,
)


def _d(item_id, version_id=None, belongs=None, current=None):
    return BundleDocumentDescriptor(
        document_item_id=item_id,
        document_version_id=version_id,
        version_belongs_to_item=belongs,
        version_is_current=current,
    )


# --------------------------------------------------------------------------
# Descriptor validation
# --------------------------------------------------------------------------


def test_descriptor_rejects_empty_item_id():
    with pytest.raises(ValueError, match="non-empty"):
        _d("  ")


def test_descriptor_strips_item_id():
    assert _d("  abc  ").document_item_id == "abc"


def test_descriptor_is_frozen_and_forbids_extra():
    d = _d("a", "v1", True, True)
    with pytest.raises(Exception):
        d.document_item_id = "b"
    with pytest.raises(ValueError):
        BundleDocumentDescriptor(document_item_id="a", bogus=1)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------


def test_all_locked_bundle_is_ok():
    ds = [
        _d("a", "v1", True, True),
        _d("b", "v2", True, True),
    ]
    r = evaluate_bundle_version_locks(ds)
    assert r.ok is True
    assert r.total == 2
    assert r.locked == 2
    assert r.unlocked == []
    assert r.mismatched == []
    assert r.stale == []


def test_missing_version_is_unlocked_and_not_ok():
    r = evaluate_bundle_version_locks([_d("a"), _d("b", "v2", True, True)])
    assert r.unlocked == ["a"]
    assert r.locked == 1
    assert r.ok is False


def test_foreign_version_is_mismatched_and_not_ok():
    r = evaluate_bundle_version_locks([_d("a", "v1", False, True)])
    assert r.mismatched == ["a"]
    assert r.locked == 0
    assert r.ok is False


def test_stale_counts_as_locked_and_does_not_fail_gate():
    r = evaluate_bundle_version_locks([_d("a", "v1", True, False)])
    assert r.stale == ["a"]
    assert r.locked == 1  # stale is NOT subtracted
    assert r.unlocked == []
    assert r.mismatched == []
    assert r.ok is True


def test_unlocked_takes_precedence_over_mismatch_check():
    # No version id -> unlocked, even though belongs is False.
    r = evaluate_bundle_version_locks([_d("a", None, False, False)])
    assert r.unlocked == ["a"]
    assert r.mismatched == []


def test_mismatch_takes_precedence_over_stale_check():
    r = evaluate_bundle_version_locks([_d("a", "v1", False, False)])
    assert r.mismatched == ["a"]
    assert r.stale == []


def test_locked_arithmetic_holds_for_mixed_bundle():
    ds = [
        _d("ok", "v1", True, True),
        _d("stale", "v2", True, False),
        _d("none"),
        _d("foreign", "v3", False, True),
    ]
    r = evaluate_bundle_version_locks(ds)
    assert r.total == 4
    assert r.unlocked == ["none"]
    assert r.mismatched == ["foreign"]
    assert r.stale == ["stale"]
    assert r.locked == r.total - len(r.unlocked) - len(r.mismatched)
    assert r.locked == 2
    assert r.ok is False


def test_belongs_none_is_not_mismatched():
    # Only an explicit False is a mismatch; None (unknown) is not.
    r = evaluate_bundle_version_locks([_d("a", "v1", None, True)])
    assert r.mismatched == []
    assert r.locked == 1
    assert r.ok is True


def test_current_none_is_not_stale():
    r = evaluate_bundle_version_locks([_d("a", "v1", True, None)])
    assert r.stale == []
    assert r.ok is True


def test_empty_bundle_is_trivially_ok():
    r = evaluate_bundle_version_locks([])
    assert r.total == 0
    assert r.locked == 0
    assert r.ok is True


# --------------------------------------------------------------------------
# Report / raise split
# --------------------------------------------------------------------------


def test_evaluate_never_raises_and_takes_no_flag():
    sig = inspect.signature(evaluate_bundle_version_locks)
    params = [p for p in sig.parameters if p != "self"]
    assert params == ["descriptors"]  # no enforcement flag
    # Bad bundle still returns a report, no exception.
    r = evaluate_bundle_version_locks([_d("a"), _d("b", "v", False)])
    assert isinstance(r, BundleLockReport)
    assert r.ok is False


def test_assert_returns_none_when_ok():
    assert assert_bundle_version_locks([_d("a", "v1", True, True)]) is None


def test_assert_raises_listing_offending_ids():
    with pytest.raises(ValueError) as exc:
        assert_bundle_version_locks([_d("a"), _d("b", "v", False, True)])
    msg = str(exc.value)
    assert "a" in msg  # unlocked id
    assert "b" in msg  # mismatched id
    assert "unlocked" in msg and "mismatched" in msg


def test_assert_does_not_raise_on_stale_only():
    # stale must never fail the gate.
    assert assert_bundle_version_locks([_d("a", "v1", True, False)]) is None


# --------------------------------------------------------------------------
# Purity guard
# --------------------------------------------------------------------------


def test_module_has_no_db_or_plugin_imports():
    import ast

    tree = ast.parse(inspect.getsource(mod))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    joined = " ".join(imported)
    for forbidden in (
        "yuantus.database",
        "sqlalchemy",
        "yuantus.meta_engine.services.file_service",
        "parallel_tasks_service",
        "plugins",
    ):
        assert forbidden not in joined, (
            f"contract must stay pure: imports {forbidden!r}"
        )


def test_evaluate_has_no_db_parameter():
    sig = inspect.signature(evaluate_bundle_version_locks)
    for name in sig.parameters:
        assert name in {"descriptors"}


# --------------------------------------------------------------------------
# Drift guard vs R1 serialize_link
# --------------------------------------------------------------------------


def test_descriptor_fields_subset_of_r1_serialize_link_keys():
    from yuantus.meta_engine.services.parallel_tasks_service import (
        WorkorderDocumentPackService,
    )

    # document_version_id=None -> serialize_link never touches the session,
    # so we can introspect its key set purely.
    fake_link = SimpleNamespace(
        id="l1",
        routing_id="r1",
        operation_id=None,
        document_item_id="i1",
        inherit_to_children=True,
        visible_in_production=True,
        document_version_id=None,
        version_locked_at=None,
        version_lock_source=None,
        created_at=None,
    )
    # MagicMock session: serialize_link does not touch it for a
    # version-less link today, but a MagicMock keeps this drift guard
    # robust if an incidental session call is added later — the test then
    # still fails on the intended key-set mismatch, not an AttributeError.
    svc = WorkorderDocumentPackService(session=MagicMock())
    keys = set(svc.serialize_link(fake_link).keys())

    descriptor_fields = set(BundleDocumentDescriptor.model_fields.keys())
    missing = descriptor_fields - keys
    assert not missing, (
        "BundleDocumentDescriptor drifted from R1 serialize_link output; "
        f"fields absent there: {missing}"
    )
