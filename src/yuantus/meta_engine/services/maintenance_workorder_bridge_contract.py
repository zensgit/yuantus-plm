"""Maintenance ↔ workorder bridge contract (R1, pure, contract-only).

Given caller-supplied descriptors of (workcenter, equipment, equipment
status, active maintenance-request state), this module answers a single
question purely: **is a workcenter blocked by maintenance?**

It mirrors the proven shape of the consumption MES contract (`6973a4c`)
and the pack-and-go version-lock bridge (`c7e6fd5`):

- **no DB / Session / I/O**; it imports only the maintenance *enums*
  (the source of truth for the value domains) — never the maintenance
  service, a router, the database layer, sqlalchemy, or any plugin;
- the pure evaluator only *reports* and never raises; enforcement is an
  explicit, separate call;
- value domains are validated against the **live** maintenance enums so
  an unknown status/state fails fast (the #570 review lesson) and a
  drift test fails loudly if those enums change.

Resolving descriptors from real ``Equipment`` / ``MaintenanceRequest``
rows (a DB resolver) and wiring the manufacturing side to call the
assertion are deliberately out of scope — each is its own separate,
later opt-in.

See ``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_MAINTENANCE_WORKORDER_BRIDGE_CONTRACT_20260515.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, field_validator

# Enum value domains are the single source of truth. Importing the enum
# classes (not the service / ORM session) is what makes the drift guard
# real: if these change, validation and the drift test move with them.
from yuantus.meta_engine.maintenance.models import (
    EquipmentStatus,
    MaintenanceRequestState,
)

_EQUIPMENT_STATUS_VALUES = frozenset(s.value for s in EquipmentStatus)
_REQUEST_STATE_VALUES = frozenset(s.value for s in MaintenanceRequestState)

# Equipment whose status is one of these is blocked outright.
_BLOCKING_EQUIPMENT_STATUSES = frozenset(
    {EquipmentStatus.OUT_OF_SERVICE.value, EquipmentStatus.DECOMMISSIONED.value}
)
# An active maintenance request in one of these states blocks the
# workcenter. `draft` is intentionally NOT here: a draft request is not
# yet active. This deliberately differs from
# MaintenanceService.get_maintenance_queue_summary, which counts `draft`
# into the active queue — that answers "is there queued work?", this
# answers "is the workcenter blocked right now?".
_BLOCKING_REQUEST_STATES = frozenset(
    {
        MaintenanceRequestState.SUBMITTED.value,
        MaintenanceRequestState.IN_PROGRESS.value,
    }
)
# Impaired but not blocking — informational only, never fails `ready`
# (same tier as the pack-and-go contract's `stale`).
_DEGRADED_EQUIPMENT_STATUS = EquipmentStatus.IN_MAINTENANCE.value


class WorkcenterMaintenanceDescriptor(BaseModel):
    """One equipment's already-resolved maintenance facts for a workcenter.

    Field names / value domains mirror the maintenance model so a future
    DB resolver maps 1:1 and the drift test can assert alignment.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    workcenter_id: str
    equipment_id: str
    equipment_status: str
    active_request_state: Optional[str] = None

    @field_validator("workcenter_id", "equipment_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("must be a non-empty string")
        return cleaned

    @field_validator("equipment_status")
    @classmethod
    def _known_equipment_status(cls, value: str) -> str:
        if value not in _EQUIPMENT_STATUS_VALUES:
            raise ValueError(
                f"equipment_status must be one of {sorted(_EQUIPMENT_STATUS_VALUES)}"
            )
        return value

    @field_validator("active_request_state")
    @classmethod
    def _known_request_state(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if value not in _REQUEST_STATE_VALUES:
            raise ValueError(
                "active_request_state must be one of "
                f"{sorted(_REQUEST_STATE_VALUES)} or null"
            )
        return value


@dataclass(frozen=True)
class WorkcenterReadinessReport:
    """Pure per-workcenter readiness result.

    ``ready`` is True iff ``blocked`` is empty. ``degraded`` is
    informational only and never affects ``ready``.
    """

    workcenter_id: str
    total_equipment: int
    blocked: List[str]
    degraded: List[str]
    ready: bool


def _is_blocked(d: WorkcenterMaintenanceDescriptor) -> bool:
    if d.equipment_status in _BLOCKING_EQUIPMENT_STATUSES:
        return True
    if d.active_request_state in _BLOCKING_REQUEST_STATES:
        return True
    return False


def evaluate_workcenter_readiness(
    descriptors: Sequence[WorkcenterMaintenanceDescriptor],
) -> List[WorkcenterReadinessReport]:
    """Pure classification, one report per distinct workcenter.

    No DB, no I/O, never raises, no enforcement flag. Reports are sorted
    by ``workcenter_id`` for deterministic output. ``draft`` /
    ``done`` / ``cancelled`` request states are non-blocking; only
    ``submitted`` / ``in_progress`` (or an out-of-service /
    decommissioned status) block. ``in_maintenance`` without a blocking
    request is ``degraded`` (never fails ``ready``).
    """

    grouped: dict[str, dict[str, List[str]]] = {}
    order: List[str] = []
    for d in descriptors:
        bucket = grouped.get(d.workcenter_id)
        if bucket is None:
            bucket = {"all": [], "blocked": [], "degraded": []}
            grouped[d.workcenter_id] = bucket
            order.append(d.workcenter_id)
        bucket["all"].append(d.equipment_id)
        if _is_blocked(d):
            bucket["blocked"].append(d.equipment_id)
        elif d.equipment_status == _DEGRADED_EQUIPMENT_STATUS:
            bucket["degraded"].append(d.equipment_id)

    reports: List[WorkcenterReadinessReport] = []
    for wc in sorted(order):
        bucket = grouped[wc]
        reports.append(
            WorkcenterReadinessReport(
                workcenter_id=wc,
                total_equipment=len(bucket["all"]),
                blocked=bucket["blocked"],
                degraded=bucket["degraded"],
                ready=not bucket["blocked"],
            )
        )
    return reports


def assert_workcenter_ready(
    descriptors: Sequence[WorkcenterMaintenanceDescriptor],
    *,
    workcenter_id: str,
) -> None:
    """Raise ``ValueError`` unless ``workcenter_id`` is maintenance-ready.

    An **absent** workcenter (no descriptor mentions it) is NOT
    vacuously ready: "no facts" means "unknown", and unknown must not
    pass. This is deliberately different from the pack-and-go
    empty-bundle decision (there, an empty bundle has no documents to
    violate; here, an absent workcenter has unknown maintenance state).

    The three failure modes carry machine-matchable message prefixes so
    a caller can react differently without catching ``ValueError``
    blindly:

    - ``workcenter_invalid:`` — empty/blank ``workcenter_id`` argument
      (caller bug).
    - ``workcenter_blocked:`` — known state, currently blocked
      (transient; a retry later may succeed).
    - ``workcenter_unknown:`` — no descriptors for this workcenter
      (not transient; likely a resolver/caller bug, do not retry).
    """

    target = (workcenter_id or "").strip()
    if not target:
        # Distinct from "unknown workcenter": this is a caller bug, not a
        # data gap. Fail with its own discriminator.
        raise ValueError(
            "workcenter_invalid: workcenter_id must be a non-empty string"
        )
    for report in evaluate_workcenter_readiness(descriptors):
        if report.workcenter_id == target:
            if report.ready:
                return
            # `workcenter_blocked:` — transient; the workcenter has known
            # maintenance state and is currently blocked.
            raise ValueError(
                f"workcenter_blocked: {target!r} is blocked by maintenance: "
                f"{len(report.blocked)} equipment "
                f"(ids={report.blocked})"
            )
    # `workcenter_unknown:` — not transient; no facts for this workcenter,
    # likely a caller/resolver bug. Callers that retry on transient
    # blockage MUST discriminate on these prefixes, not catch ValueError
    # blindly.
    raise ValueError(
        f"workcenter_unknown: {target!r} has no maintenance descriptors; "
        "readiness is unknown and must not be assumed"
    )
