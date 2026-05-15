"""Automation-rule predicate pure-contract (R1, pure, contract-only).

The rule-matching `match_predicates` logic already exists embedded in
`WorkflowCustomActionService` (`_normalize_match_predicates`,
`_rule_match_predicates`, `_rule_matches_runtime_scope`). It has no
isolated, testable, refactor-safe surface. This module extracts its
**exact current semantics** into a small **pure** contract so a
service-parity matrix can pin it bit-for-bit.

It is **behavior-preserving and parallel**: it does NOT edit the
service, the router, or anything runtime. Substituting the service to
delegate here is a separate, later opt-in.

Pure: imports only the ECO model enums for the value domains — never
`WorkflowCustomActionService`, the DB, sqlalchemy, or a router. The
service-parity *test* imports the service; this module does not.

See ``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_AUTOMATION_RULE_PREDICATE_CONTRACT_20260515.md``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, field_validator

# Value domains come from the model layer (pure), not the service. The
# drift guard test asserts these equal the service's
# _ALLOWED_ECO_PRIORITIES / _ALLOWED_ECO_TYPES so a divergence on either
# side fails loudly.
from yuantus.meta_engine.models.eco import ECOPriority, ECOType

_ALLOWED_MATCH_PREDICATE_KEYS = frozenset(
    {"stage_id", "eco_priority", "actor_roles", "product_id", "eco_type"}
)
_ALLOWED_ECO_PRIORITIES = frozenset(p.value for p in ECOPriority)
_ALLOWED_ECO_TYPES = frozenset(t.value for t in ECOType)


# --------------------------------------------------------------------------
# Normalization mirrors WorkflowCustomActionService helpers exactly.
# --------------------------------------------------------------------------


def _normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_string_list(value: Any, *, field: str) -> Tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple, set)):
        raise ValueError(f"{field} must be an array of strings")
    seen = set()
    out = []
    for raw in value:
        item = _normalize_optional_string(raw)
        if not item:
            continue
        item = item.lower()
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return tuple(out)


def _normalize_match_predicates_strict(
    match_predicates: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Pure mirror of WorkflowCustomActionService._normalize_match_predicates.

    Raises ``ValueError`` on the exact same conditions (non-dict,
    unsupported key, bad enum, non-array actor_roles). Empties dropped.
    """

    if match_predicates is None:
        return {}
    if not isinstance(match_predicates, dict):
        raise ValueError("match_predicates must be an object")

    unsupported = sorted(
        k for k in match_predicates.keys() if k not in _ALLOWED_MATCH_PREDICATE_KEYS
    )
    if unsupported:
        raise ValueError(
            "match_predicates only supports: actor_roles, eco_priority, "
            "eco_type, product_id, stage_id"
        )

    normalized: Dict[str, Any] = {}

    stage_id = _normalize_optional_string(match_predicates.get("stage_id"))
    if stage_id:
        normalized["stage_id"] = stage_id

    eco_priority = _normalize_optional_string(match_predicates.get("eco_priority"))
    if eco_priority:
        eco_priority = eco_priority.lower()
        if eco_priority not in _ALLOWED_ECO_PRIORITIES:
            raise ValueError(
                "match_predicates.eco_priority must be one of: "
                "low, normal, high, urgent"
            )
        normalized["eco_priority"] = eco_priority

    actor_roles = _normalize_string_list(
        match_predicates.get("actor_roles"),
        field="match_predicates.actor_roles",
    )
    if actor_roles:
        normalized["actor_roles"] = actor_roles

    product_id = _normalize_optional_string(match_predicates.get("product_id"))
    if product_id:
        normalized["product_id"] = product_id

    eco_type = _normalize_optional_string(match_predicates.get("eco_type"))
    if eco_type:
        eco_type = eco_type.lower()
        if eco_type not in _ALLOWED_ECO_TYPES:
            raise ValueError(
                "match_predicates.eco_type must be one of: bom, product, document"
            )
        normalized["eco_type"] = eco_type

    return normalized


# --------------------------------------------------------------------------
# DTOs
# --------------------------------------------------------------------------


class WorkflowRulePredicate(BaseModel):
    """Already-normalized rule predicate. All fields optional; absent = wildcard.

    ``workflow_map_id`` is a rule-column scope filter, modeled as an
    independent field (NOT part of match_predicates) so the fail-open
    path can preserve it while zeroing the predicate-derived keys —
    bit-for-bit with the service.

    Fields must be **already normalized**. ``normalize_workflow_rule_predicate``
    is the blessed constructor (it lowercases enums, de-dups
    ``actor_roles``, drops blanks, and fails open). Direct construction
    validates enum *membership* but does NOT normalize casing — e.g.
    ``WorkflowRulePredicate(eco_priority="HIGH")`` raises, whereas the
    factory yields ``eco_priority == "high"``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    workflow_map_id: Optional[str] = None
    stage_id: Optional[str] = None
    eco_priority: Optional[str] = None
    actor_roles: Tuple[str, ...] = ()
    product_id: Optional[str] = None
    eco_type: Optional[str] = None

    @field_validator("eco_priority")
    @classmethod
    def _known_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in _ALLOWED_ECO_PRIORITIES:
            raise ValueError(
                "eco_priority must be one of: low, normal, high, urgent"
            )
        return v

    @field_validator("eco_type")
    @classmethod
    def _known_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in _ALLOWED_ECO_TYPES:
            raise ValueError("eco_type must be one of: bom, product, document")
        return v

    def is_empty(self) -> bool:
        """True iff no constraint at all (matches everything)."""
        return (
            self.workflow_map_id is None
            and self.stage_id is None
            and self.eco_priority is None
            and not self.actor_roles
            and self.product_id is None
            and self.eco_type is None
        )


class WorkflowRuleFacts(BaseModel):
    """Runtime context counterpart, normalized like _normalize_runtime_context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    workflow_map_id: Optional[str] = None
    stage_id: Optional[str] = None
    eco_priority: Optional[str] = None
    product_id: Optional[str] = None
    eco_type: Optional[str] = None
    actor_roles: Tuple[str, ...] = ()

    @classmethod
    def from_context(cls, context: Optional[Dict[str, Any]]) -> "WorkflowRuleFacts":
        ctx = dict(context or {})
        eco_priority = _normalize_optional_string(ctx.get("eco_priority"))
        eco_type = _normalize_optional_string(ctx.get("eco_type"))
        return cls(
            workflow_map_id=_normalize_optional_string(ctx.get("workflow_map_id")),
            stage_id=_normalize_optional_string(ctx.get("stage_id")),
            eco_priority=eco_priority.lower() if eco_priority else None,
            product_id=_normalize_optional_string(ctx.get("product_id")),
            eco_type=eco_type.lower() if eco_type else None,
            actor_roles=_normalize_string_list(
                ctx.get("actor_roles"), field="context.actor_roles"
            ),
        )


def normalize_workflow_rule_predicate(
    workflow_map_id: Any,
    match_predicates: Optional[Dict[str, Any]],
) -> WorkflowRulePredicate:
    """Pure mirror of rule.workflow_map_id + _rule_match_predicates.

    ``workflow_map_id`` is normalized independently. ``match_predicates``
    is strict-normalized; **on any validation error it degrades to the
    empty predicate, but the normalized ``workflow_map_id`` is
    preserved** — bit-for-bit with WorkflowCustomActionService where
    ``workflow_map_id`` is a rule column read *before* and independent
    of the predicate fail-open path (`_rule_match_predicates` line
    2169). Raises nothing.
    """

    wf = _normalize_optional_string(workflow_map_id)
    try:
        normalized = _normalize_match_predicates_strict(match_predicates)
    except ValueError:
        # fail-open: drop predicate-derived keys, keep workflow_map_id.
        return WorkflowRulePredicate(workflow_map_id=wf)
    return WorkflowRulePredicate(
        workflow_map_id=wf,
        stage_id=normalized.get("stage_id"),
        eco_priority=normalized.get("eco_priority"),
        actor_roles=tuple(normalized.get("actor_roles", ())),
        product_id=normalized.get("product_id"),
        eco_type=normalized.get("eco_type"),
    )


def evaluate_rule_predicate(
    predicate: WorkflowRulePredicate,
    facts: WorkflowRuleFacts,
) -> bool:
    """Pure mirror of WorkflowCustomActionService._rule_matches_runtime_scope.

    Step order and "only enforced if the predicate value is truthy"
    semantics are reproduced exactly: workflow_map_id (step 1), then
    stage_id / eco_priority / product_id / eco_type equality, then
    actor_roles set-intersection. Absent = wildcard; empty = True.
    """

    if predicate.workflow_map_id and predicate.workflow_map_id != facts.workflow_map_id:
        return False
    if predicate.stage_id and predicate.stage_id != facts.stage_id:
        return False
    if predicate.eco_priority and predicate.eco_priority != facts.eco_priority:
        return False
    if predicate.product_id and predicate.product_id != facts.product_id:
        return False
    if predicate.eco_type and predicate.eco_type != facts.eco_type:
        return False
    if predicate.actor_roles:
        if not set(facts.actor_roles).intersection(predicate.actor_roles):
            return False
    return True
