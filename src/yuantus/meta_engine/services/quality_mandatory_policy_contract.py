"""Quality `is_mandatory` policy overlay (R1, pure, REPORT ONLY).

The shipped quality↔workorder gate
(`quality_workorder_gate_contract.py`, PR #581) treats every applicable
production point as blocking because `QualityPoint` has no mandatory
flag (ratified §3). This module adds a *pure* caller-supplied
**`is_mandatory` policy overlay** that refines the shipped gate report
into mandatory-blocking vs advisory — **without** touching the shipped
gate, the model, or any runtime.

Hard boundary (owner-scoped, taskbook §3/§8):

- `is_mandatory` is a **caller policy overlay**, NEVER a `QualityPoint`
  column and never added to the shipped `QualityPointDescriptor`
  (doing so would break #581's column-subset drift guard).
- **Default = mandatory.** An empty policy yields a verdict *identical*
  to the shipped gate. `is_mandatory=False` only ever *downgrades* a
  point to advisory — it can never escalate.
- This is **additive and parallel**: it imports the shipped
  `OperationQualityGateReport` **type only**, never calls
  `evaluate_operation_quality_gate`, and never edits it.
- **Report only**: no `assert_*`, no raiser, no enforcement, no DB, no
  schema, no runtime.

See ``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_QUALITY_IS_MANDATORY_POLICY_20260516.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

# Type-only reuse of the shipped report. We do NOT import or call
# evaluate_operation_quality_gate — the caller supplies the already
# built report.
from yuantus.meta_engine.services.quality_workorder_gate_contract import (
    OperationQualityGateReport,
)


@dataclass(frozen=True)
class MandatoryPolicy:
    """Immutable caller-supplied per-point mandatory policy.

    Default is **mandatory**: any point not explicitly marked
    non-mandatory is treated as mandatory (preserves the shipped
    ratified §3). Only an explicit ``False`` downgrades a point.
    """

    _non_mandatory: frozenset

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, bool]) -> "MandatoryPolicy":
        # Store only the explicit non-mandatory ids; explicit True == the
        # default True, so it need not be recorded.
        return cls(
            _non_mandatory=frozenset(
                str(k) for k, v in (mapping or {}).items() if v is False
            )
        )

    @classmethod
    def empty(cls) -> "MandatoryPolicy":
        return cls(_non_mandatory=frozenset())

    def is_mandatory(self, point_id: str) -> bool:
        return point_id not in self._non_mandatory


@dataclass(frozen=True)
class MandatoryGateReport:
    """Refinement of the shipped report under a mandatory policy.

    - ``mandatory_blocked``: unmet (blocked or missing) points the
      policy treats as mandatory — these are what actually fail.
    - ``advisory_unmet``: unmet points the policy marked
      non-mandatory — informational only, do NOT fail.
    - ``cleared``: passthrough of the shipped report's cleared points.
    - ``mandatory_ok``: ``len(mandatory_blocked) == 0``.
    """

    mandatory_blocked: Tuple[str, ...]
    advisory_unmet: Tuple[str, ...]
    cleared: Tuple[str, ...]
    mandatory_ok: bool


def classify_gate_result_by_mandatory(
    report: OperationQualityGateReport,
    policy: MandatoryPolicy,
) -> MandatoryGateReport:
    """Pure: partition the shipped report's unmet points by the policy.

    Takes an already-built ``OperationQualityGateReport`` (the caller
    runs the shipped gate). The shipped gate guarantees ``blocked`` and
    ``missing`` are disjoint and each applicable point is exactly one of
    cleared/blocked/missing, so concatenation preserves that. Default
    mandatory ⇒ an empty policy reproduces the shipped verdict exactly.
    Never recomputes the gate, reads a DB, or raises.
    """

    unmet = tuple(report.blocked) + tuple(report.missing)
    mandatory_blocked = tuple(
        pid for pid in unmet if policy.is_mandatory(pid)
    )
    advisory_unmet = tuple(
        pid for pid in unmet if not policy.is_mandatory(pid)
    )
    return MandatoryGateReport(
        mandatory_blocked=mandatory_blocked,
        advisory_unmet=advisory_unmet,
        cleared=tuple(report.cleared),
        mandatory_ok=not mandatory_blocked,
    )
