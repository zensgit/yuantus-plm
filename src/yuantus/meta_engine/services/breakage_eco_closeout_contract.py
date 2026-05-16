"""Breakage → ECO closeout contract (R1, pure, contract-only).

A field breakage that turns out to be a design defect should loop back
into engineering as a change. `BreakageIncident` (data plane) and
`ChangeRequestIntake` (ECO-intake plane, the shipped ECR intake
contract) both exist; this module is the **pure, typed bridge** between
them.

It is **pure and parallel**: no DB, no `create_eco`, no
`BreakageIncident` write, no state-machine edit, no router/schema
change. It **reuses** `ecr_intake_contract` as a pure dependency
(never modifies it). Imports only that contract and the ECO model
enums — never `parallel_tasks_service`, the DB, sqlalchemy, or a
router.

Two policies here are **owner-RATIFIED** (binding, test-pinned; not
reviewer choices) — see
``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_BREAKAGE_ECO_CLOSEOUT_CONTRACT_20260515.md``
§3:

- ``eligible_statuses = {"resolved", "closed"}`` — open / in_progress /
  any unknown status are NOT eligible.
- ``severity_to_priority`` table + **unknown severity → "normal"** as
  an explicit *conservative downgrade policy* (NOT a silent fallback):
  dirty data is neither escalated to urgent/high nor dropped.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from yuantus.meta_engine.services.ecr_intake_contract import ChangeRequestIntake

CONTRACT_VERSION = "breakage-eco-closeout.v1"

# RATIFIED policy §3.1 — exact constant name is binding.
eligible_statuses = frozenset({"resolved", "closed"})

# RATIFIED policy §3.2 — exact constant name + literal table are
# binding. Any severity NOT in this table maps to "normal" (see
# _UNKNOWN_SEVERITY_PRIORITY). This is a documented conservative
# *downgrade* policy, never a silent fallback.
severity_to_priority = {
    "critical": "urgent",
    "high": "high",
    "medium": "normal",
    "low": "low",
}
_UNKNOWN_SEVERITY_PRIORITY = "normal"

_KEY_SEP = "\x1f"


def _norm(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


class BreakageEcoClosureDescriptor(BaseModel):
    """Already-resolved breakage facts the bridge needs.

    Field names mirror the ``BreakageIncident`` columns so a future DB
    resolver maps 1:1 and a drift test asserts alignment.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str
    status: str
    severity: str = "medium"
    incident_code: Optional[str] = None
    product_item_id: Optional[str] = None
    bom_id: Optional[str] = None
    version_id: Optional[str] = None

    @field_validator("description")
    @classmethod
    def _description_non_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("description must be a non-empty string")
        return s

    @field_validator("status", "severity")
    @classmethod
    def _required_lower(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if not s:
            raise ValueError("must be a non-empty string")
        return s

    @field_validator("incident_code", "product_item_id", "bom_id", "version_id")
    @classmethod
    def _blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        return _norm(v)


def is_breakage_eligible_for_design_loopback(
    descriptor: BreakageEcoClosureDescriptor,
) -> bool:
    """RATIFIED §3.1: True iff status ∈ ``eligible_statuses``.

    ``status`` is already normalized (lower/trimmed) by the descriptor
    validator, so ``open`` / ``in_progress`` / any unknown value are
    NOT eligible.
    """

    return descriptor.status in eligible_statuses


def severity_priority(severity: str) -> str:
    """RATIFIED §3.2: pinned table; anything else → ``"normal"``.

    The ``unknown → "normal"`` rule is a deliberate, documented
    conservative *downgrade* policy — NOT a silent fallback.
    """

    return severity_to_priority.get(
        (severity or "").strip().lower(), _UNKNOWN_SEVERITY_PRIORITY
    )


def derive_breakage_change_reference(
    descriptor: BreakageEcoClosureDescriptor,
) -> str:
    """Deterministic reference for a breakage→change loopback.

    Recorded in the reason envelope only — **not enforced** (no dedupe,
    no DB), same deferral as the ECR / consumption references.
    """

    material = _KEY_SEP.join(
        (
            descriptor.incident_code or "",
            descriptor.product_item_id or "",
            descriptor.version_id or "",
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def map_breakage_to_change_request_intake(
    descriptor: BreakageEcoClosureDescriptor,
) -> ChangeRequestIntake:
    """Pure map: eligible breakage → ECR ``ChangeRequestIntake``.

    Raises ``ValueError`` if the descriptor is not eligible (callers
    must gate on ``is_breakage_eligible_for_design_loopback`` first).
    Reuses the shipped ECR intake contract; does NOT call
    ``create_eco`` or touch any DB.
    """

    if not is_breakage_eligible_for_design_loopback(descriptor):
        raise ValueError(
            f"breakage status {descriptor.status!r} is not eligible for "
            f"design loopback (eligible: {sorted(eligible_statuses)})"
        )

    # bom ⇒ product_id invariant of ChangeRequestIntake: only claim
    # change_type="bom" when we can also supply a product_id. A bom_id
    # without a product_item_id falls back to "product" to stay valid.
    if descriptor.bom_id and descriptor.product_item_id:
        change_type = "bom"
    else:
        change_type = "product"

    reference = derive_breakage_change_reference(descriptor)
    envelope = (
        f"[breakage-eco-closeout contract_version={CONTRACT_VERSION} "
        f"incident={descriptor.incident_code or ''} "
        f"version={descriptor.version_id or ''} "
        f"reference={reference}]"
    )
    title = f"Design loopback: {descriptor.incident_code or 'breakage'}"

    return ChangeRequestIntake(
        title=title,
        change_type=change_type,
        product_id=descriptor.product_item_id,
        priority=severity_priority(descriptor.severity),
        reason=f"{descriptor.description}\n\n{envelope}",
        requester_user_id=None,
    )
