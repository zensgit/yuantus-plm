"""ECR dedupe pure-contract (R1, pure, REPORT ONLY).

The shipped ECR intake contract derives a deterministic
`derive_change_request_reference(intake)` but explicitly does not
enforce uniqueness. This module adds the missing pure piece: a
**collision report** over a set of change-request intakes.

Hard boundary (owner-scoped, taskbook §3/§8): **report only**. There is
no `assert_*`, no raiser, no enforcement, no merge/drop/reject, no DB,
no schema. `ecr_intake_contract` is reused **unchanged** — the
reference is imported, never reimplemented (drift-guarded by the test).

Pure: imports only `ecr_intake_contract`. Never imports the DB,
sqlalchemy, a router, a plugin, or any `*_service`.

See ``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_ECR_DEDUPE_CONTRACT_20260516.md``.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from yuantus.meta_engine.services.ecr_intake_contract import (
    ChangeRequestIntake,
    derive_change_request_reference,
)


@dataclass(frozen=True)
class ChangeRequestReferenceCollision:
    """One reference shared by ≥2 caller-supplied intakes.

    ``keys`` are the caller's own keys (input order preserved).
    """

    reference: str
    keys: Tuple[str, ...]


@dataclass(frozen=True)
class ChangeRequestDedupeReport:
    """Pure dedupe report — informational, not a gate.

    ``has_collisions`` is a neutral name on purpose: this is a report,
    not an enforcement decision. There is no ``ok``.
    """

    total: int
    unique_references: int
    collisions: Tuple[ChangeRequestReferenceCollision, ...]
    has_collisions: bool


def build_change_request_dedupe_report(
    items: Sequence[Tuple[str, ChangeRequestIntake]],
) -> ChangeRequestDedupeReport:
    """Pure: group caller items by derived reference; report collisions.

    ``items`` is a sequence of ``(caller_key, ChangeRequestIntake)``.
    The reference is obtained via the **imported**
    ``derive_change_request_reference`` (reused, never reimplemented).
    A reference shared by ≥2 keys is a collision. Duplicate caller keys
    are allowed — the caller owns key semantics; this only groups by
    reference. Output is deterministic: ``collisions`` sorted by
    ``reference``, each group's ``keys`` in input order.
    """

    grouped: "OrderedDict[str, List[str]]" = OrderedDict()
    for key, intake in items:
        reference = derive_change_request_reference(intake)
        grouped.setdefault(reference, []).append(key)

    collisions = tuple(
        ChangeRequestReferenceCollision(reference=ref, keys=tuple(keys))
        for ref, keys in sorted(grouped.items())
        if len(keys) >= 2
    )

    return ChangeRequestDedupeReport(
        total=len(items),
        unique_references=len(grouped),
        collisions=collisions,
        has_collisions=bool(collisions),
    )
