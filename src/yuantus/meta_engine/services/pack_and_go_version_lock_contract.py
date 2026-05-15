"""Pack-and-go version-lock bridge contract (R1, pure, contract-only).

RFC #568 selected Option C: do NOT mainline the pack-and-go plugin.
Instead expose a small *pure* contract that lets a caller assert "every
document in a bundle is version-pinned and belongs to its item", reusing
the workorder version-lock R1 ownership semantics (PR #565, ``12456d3``).

This module:

- has **no DB / Session / I/O** and imports nothing from the plugin,
  routers, or the database layer — it operates only on caller-supplied
  descriptors;
- never mutates input and never performs enforcement implicitly: the
  pure evaluator only *reports*; raising is an explicit, separate call;
- mirrors R1's ``version_lock_summary`` arithmetic exactly so the two
  surfaces cannot silently diverge (guarded by a drift test).

Resolving descriptors from real item/file/version rows (a DB resolver)
and wiring the plugin to call the assertion are deliberately out of
scope here — each is its own separate, later opt-in.

See ``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_PACK_AND_GO_VERSION_LOCK_BRIDGE_CONTRACT_20260515.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, field_validator


class BundleDocumentDescriptor(BaseModel):
    """One document's already-resolved version-lock facts.

    Field names deliberately mirror the keys produced by R1
    ``WorkorderDocumentPackService.serialize_link`` so a future DB
    resolver can map 1:1 and the drift test can assert alignment.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_item_id: str
    document_version_id: Optional[str] = None
    version_belongs_to_item: Optional[bool] = None
    version_is_current: Optional[bool] = None

    @field_validator("document_item_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("document_item_id must be a non-empty string")
        return cleaned


@dataclass(frozen=True)
class BundleLockReport:
    """Pure evaluation result for a bundle.

    ``locked`` is defined exactly as R1's ``version_lock_summary``:
    ``locked = total - len(unlocked) - len(mismatched)``. A
    version-present-but-mismatched descriptor is not counted as locked.
    A ``stale`` descriptor (locked & owned but not current) still counts
    as locked — stale is informational only and never fails the gate.
    """

    total: int
    locked: int
    unlocked: List[str]
    mismatched: List[str]
    stale: List[str]
    ok: bool


def evaluate_bundle_version_locks(
    descriptors: Sequence[BundleDocumentDescriptor],
) -> BundleLockReport:
    """Pure classification of a bundle's version-lock state.

    No DB, no I/O, never raises, takes no enforcement flag. ``ok`` is
    fully determined by ``unlocked``/``mismatched``; the decision to
    block an export is the caller's (see ``assert_bundle_version_locks``
    or future wiring).

    Precedence: a descriptor with no version is ``unlocked`` (and not
    also checked for ownership). A descriptor with a version whose
    ownership is **not positively confirmed** —
    ``version_belongs_to_item is not True`` (i.e. ``False`` *or* unknown
    ``None``) — is ``mismatched``. A confirmed-owned descriptor with
    ``version_is_current is False`` is ``stale`` (still locked).

    Note on R1 alignment: R1 ``export_pack`` only ever sees a resolved
    boolean ``version_belongs_to_item`` when a version is present (the
    DB lookup sets it), so on R1-shaped data ``is not True`` and
    ``is False`` are equivalent. The stronger ``is not True`` check only
    matters for *caller-supplied* descriptors, where unknown ownership
    must not silently pass — the contract guarantees "version-pinned and
    confirmed to belong to its item", not "pinned and not explicitly
    foreign".
    """

    unlocked: List[str] = []
    mismatched: List[str] = []
    stale: List[str] = []

    for d in descriptors:
        if not d.document_version_id:
            unlocked.append(d.document_item_id)
            continue
        if d.version_belongs_to_item is not True:
            mismatched.append(d.document_item_id)
            continue
        if d.version_is_current is False:
            stale.append(d.document_item_id)

    total = len(descriptors)
    locked = total - len(unlocked) - len(mismatched)
    ok = not unlocked and not mismatched
    return BundleLockReport(
        total=total,
        locked=locked,
        unlocked=unlocked,
        mismatched=mismatched,
        stale=stale,
        ok=ok,
    )


def assert_bundle_version_locks(
    descriptors: Sequence[BundleDocumentDescriptor],
) -> None:
    """Raise ``ValueError`` if the bundle is not fully version-locked.

    Thin enforcement wrapper so a future opted-in caller (e.g. the
    pack-and-go plugin) can block an export without re-deriving the
    classification. Returns ``None`` when ``ok``.
    """

    report = evaluate_bundle_version_locks(descriptors)
    if report.ok:
        return
    raise ValueError(
        "bundle has version-lock violations: "
        f"{len(report.unlocked)} unlocked (ids={report.unlocked}) + "
        f"{len(report.mismatched)} mismatched (ids={report.mismatched})"
    )
