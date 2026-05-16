"""Quality ↔ workorder gate contract (R1, pure, contract-only).

Decides "is this operation quality-clear?" purely, over caller-supplied
descriptors. It **activates the dormant `QualityPoint.trigger_on ==
"production"` semantics** in a testable form.

Honest scope (see the taskbook §2): there is NO operation/workorder
execution runtime in the codebase and `trigger_on` is consumed
nowhere. So this module is a pure gate + a **default-OFF enforcement
seam** (`assert_operation_quality_clear`) that nothing calls — merging
it changes no behavior. True runtime enforcement is doubly gated on a
workorder-execution domain that does not exist (separate opt-ins).

Pure: imports only the `QualityCheckResult` enum for the value domain.
It never imports `QualityService`, the manufacturing layer, a router,
the DB, or sqlalchemy. The drift-guard *test* imports the models /
service; this module does not.

See ``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_QUALITY_WORKORDER_RUNTIME_CONTRACT_20260515.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, field_validator

from yuantus.meta_engine.quality.models import QualityCheckResult

_RESULT_VALUES = frozenset(r.value for r in QualityCheckResult)

# RATIFIED §3: only "pass" clears; fail/warning/none/missing block.
_CLEARING_RESULT = QualityCheckResult.PASS.value

# The dormant trigger that this contract activates. The drift-guard
# test asserts this literal is still in the trigger_on vocabulary
# validated by QualityService.create_point.
_PRODUCTION_TRIGGER = "production"


def _norm(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _scope_matches(descriptor_value: Optional[str], facts_value: Optional[str]) -> bool:
    """§4.1: None on the descriptor = wildcard; non-None must equal facts."""
    return descriptor_value is None or descriptor_value == facts_value


class OperationQualityFacts(BaseModel):
    """The operation context the caller resolved."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    product_id: Optional[str] = None
    item_type_id: Optional[str] = None
    routing_id: Optional[str] = None
    operation_id: Optional[str] = None

    @field_validator("product_id", "item_type_id", "routing_id", "operation_id")
    @classmethod
    def _blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        return _norm(v)


class QualityPointDescriptor(BaseModel):
    """Mirrors the `QualityPoint` fields the gate needs (4 scope fields)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    trigger_on: str
    is_active: bool = True
    product_id: Optional[str] = None
    item_type_id: Optional[str] = None
    routing_id: Optional[str] = None
    operation_id: Optional[str] = None

    @field_validator("id")
    @classmethod
    def _id_non_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("id must be a non-empty string")
        return s

    @field_validator("product_id", "item_type_id", "routing_id", "operation_id")
    @classmethod
    def _blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        return _norm(v)

    def scope_matches(self, facts: "OperationQualityFacts") -> bool:
        return (
            _scope_matches(self.product_id, facts.product_id)
            and _scope_matches(self.item_type_id, facts.item_type_id)
            and _scope_matches(self.routing_id, facts.routing_id)
            and _scope_matches(self.operation_id, facts.operation_id)
        )


class QualityCheckDescriptor(BaseModel):
    """Mirrors the `QualityCheck` fields the gate needs (3 scope fields).

    `QualityCheck` has **no** `item_type_id` column — that asymmetry is
    real and modeled honestly here (item_type_id is NOT a check scope
    constraint).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    point_id: str
    result: str
    product_id: Optional[str] = None
    routing_id: Optional[str] = None
    operation_id: Optional[str] = None

    @field_validator("point_id")
    @classmethod
    def _point_id_non_empty(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("point_id must be a non-empty string")
        return s

    @field_validator("result")
    @classmethod
    def _known_result(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if s not in _RESULT_VALUES:
            raise ValueError(
                f"result must be one of {sorted(_RESULT_VALUES)}"
            )
        return s

    @field_validator("product_id", "routing_id", "operation_id")
    @classmethod
    def _blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        return _norm(v)

    def scope_matches(self, facts: "OperationQualityFacts") -> bool:
        return (
            _scope_matches(self.product_id, facts.product_id)
            and _scope_matches(self.routing_id, facts.routing_id)
            and _scope_matches(self.operation_id, facts.operation_id)
        )


@dataclass(frozen=True)
class OperationQualityGateReport:
    """Pure gate result.

    - ``cleared``: applicable point ids with a scope-matching ``pass``.
    - ``blocked``: applicable point ids whose only scope-matching
      checks are ``fail``/``warning``/``none`` (a check exists, none
      pass).
    - ``missing``: applicable point ids with no scope-matching check.
    - ``ok`` iff both ``blocked`` and ``missing`` are empty.
    """

    total: int
    cleared: List[str]
    blocked: List[str]
    missing: List[str]
    ok: bool


def resolve_applicable_quality_points(
    facts: OperationQualityFacts,
    points: Sequence[QualityPointDescriptor],
) -> Tuple[QualityPointDescriptor, ...]:
    """§4.3: active, production-triggered points whose 4-field scope matches."""
    return tuple(
        p
        for p in points
        if p.is_active
        and p.trigger_on == _PRODUCTION_TRIGGER
        and p.scope_matches(facts)
    )


def evaluate_operation_quality_gate(
    facts: OperationQualityFacts,
    points: Sequence[QualityPointDescriptor],
    checks: Sequence[QualityCheckDescriptor],
) -> OperationQualityGateReport:
    """Pure, never raises. RATIFIED §3: only ``pass`` clears.

    A point is cleared iff there exists a check with
    ``check.point_id == point.id`` AND ``check.result == "pass"`` AND
    the check's 3-field scope matches ``facts`` (the per-check scope
    filter prevents a cross-product/routing/operation pass from
    clearing the wrong point).
    """
    applicable = resolve_applicable_quality_points(facts, points)
    cleared: List[str] = []
    blocked: List[str] = []
    missing: List[str] = []
    for point in applicable:
        scoped = [
            c
            for c in checks
            if c.point_id == point.id and c.scope_matches(facts)
        ]
        if any(c.result == _CLEARING_RESULT for c in scoped):
            cleared.append(point.id)
        elif scoped:
            blocked.append(point.id)
        else:
            missing.append(point.id)
    ok = not blocked and not missing
    return OperationQualityGateReport(
        total=len(applicable),
        cleared=cleared,
        blocked=blocked,
        missing=missing,
        ok=ok,
    )


def assert_operation_quality_clear(
    facts: OperationQualityFacts,
    points: Sequence[QualityPointDescriptor],
    checks: Sequence[QualityCheckDescriptor],
) -> None:
    """Default-OFF enforcement seam.

    Raises ``ValueError`` listing the offending (blocked + missing)
    point ids when the operation is not quality-clear; returns ``None``
    when clear. **Nothing in the codebase calls this** (there is no
    operation-completion path) — merging R1 changes no behavior.
    """
    report = evaluate_operation_quality_gate(facts, points, checks)
    if report.ok:
        return
    raise ValueError(
        "operation not quality-clear: "
        f"{len(report.blocked)} blocked (ids={report.blocked}) + "
        f"{len(report.missing)} missing (ids={report.missing})"
    )
