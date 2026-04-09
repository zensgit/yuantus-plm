"""Shared governance discoverability contracts for subcontracting router payloads."""
from __future__ import annotations

from typing import Dict, Sequence, Tuple, Union

GovernanceLinkSpec = Union[str, Tuple[str, str]]

GOVERNANCE_DISCOVERABILITY_PATHS: Dict[str, str] = {
    "governance_inbox": "/api/v1/subcontracting/governance-inbox",
    "governance_action": "/api/v1/subcontracting/governance-inbox/action",
    "governance_review_digest": "/api/v1/subcontracting/governance-inbox/review-digest",
    "governance_review_handoff": "/api/v1/subcontracting/governance-inbox/review-handoff",
    "governance_review_handoff_accept": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/accept"
    ),
    "governance_review_handoff_history": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/history"
    ),
    "governance_review_handoff_acceptance_digest": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-digest"
    ),
    "governance_review_handoff_acceptance_entry_efficiency": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency"
    ),
    "governance_review_handoff_acceptance_follow_through_digest": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest"
    ),
    "governance_review_handoff_acceptance_follow_through_history": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-history"
    ),
    "governance_review_handoff_acceptance_follow_through_burndown": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown"
    ),
    "governance_review_handoff_acceptance_trends": (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-trends"
    ),
    "governance_presets": "/api/v1/subcontracting/governance-inbox/presets",
    "governance_correlation_presets": (
        "/api/v1/subcontracting/governance-inbox/correlation-presets"
    ),
    "governance_correlation": "/api/v1/subcontracting/governance-inbox/correlation-board",
    "governance_burndown": "/api/v1/subcontracting/governance-inbox/burndown",
    "governance_sla_board": "/api/v1/subcontracting/governance-inbox/sla-board",
    "governance_history": "/api/v1/subcontracting/governance-inbox/history",
    "approval_inbox": "/api/v1/subcontracting/return-disposition-approval-inbox",
    "role_mappings": "/api/v1/subcontracting/approval-role-mappings",
    "cleanup_apply_preview": (
        "/api/v1/subcontracting/approval-role-mappings/cleanup-apply-preview"
    ),
    "cleanup_policy_board": (
        "/api/v1/subcontracting/approval-role-mappings/cleanup-policy-board"
    ),
    "rollback_burndown": (
        "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
    ),
    "rollback_board": (
        "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
    ),
    "alert_assign": (
        "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-alert-assign"
    ),
    "alert_control": (
        "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-alert-control"
    ),
}

GOVERNANCE_REVIEW_DISCOVERABILITY_SPECS: Tuple[GovernanceLinkSpec, ...] = (
    "governance_inbox",
    "governance_presets",
    "governance_review_digest",
    "governance_review_handoff",
    "governance_review_handoff_accept",
    "governance_review_handoff_history",
    "governance_review_handoff_acceptance_digest",
    "governance_review_handoff_acceptance_entry_efficiency",
    "governance_review_handoff_acceptance_follow_through_digest",
    "governance_review_handoff_acceptance_follow_through_history",
    "governance_review_handoff_acceptance_follow_through_burndown",
    "governance_review_handoff_acceptance_trends",
    "governance_correlation_presets",
    "governance_correlation",
    "governance_burndown",
    "governance_sla_board",
    "governance_history",
    "governance_action",
)

GOVERNANCE_ROOT_DISCOVERABILITY_SPECS: Tuple[GovernanceLinkSpec, ...] = (
    ("action", "governance_action"),
    ("review_digest", "governance_review_digest"),
    ("review_handoff", "governance_review_handoff"),
    ("review_handoff_accept", "governance_review_handoff_accept"),
    ("review_handoff_history", "governance_review_handoff_history"),
    ("review_handoff_acceptance_digest", "governance_review_handoff_acceptance_digest"),
    (
        "review_handoff_acceptance_entry_efficiency",
        "governance_review_handoff_acceptance_entry_efficiency",
    ),
    (
        "review_handoff_acceptance_follow_through_digest",
        "governance_review_handoff_acceptance_follow_through_digest",
    ),
    (
        "review_handoff_acceptance_follow_through_history",
        "governance_review_handoff_acceptance_follow_through_history",
    ),
    (
        "review_handoff_acceptance_follow_through_burndown",
        "governance_review_handoff_acceptance_follow_through_burndown",
    ),
    ("review_handoff_acceptance_trends", "governance_review_handoff_acceptance_trends"),
    ("presets", "governance_presets"),
    ("correlation_presets", "governance_correlation_presets"),
    ("burndown", "governance_burndown"),
    ("correlation_board", "governance_correlation"),
    ("sla_board", "governance_sla_board"),
    ("history", "governance_history"),
    ("approval_inbox", "approval_inbox"),
    ("cleanup_policy_board", "cleanup_policy_board"),
    ("rollback_burndown", "rollback_burndown"),
)

GOVERNANCE_ACTION_SUPPORT_SPECS: Tuple[GovernanceLinkSpec, ...] = (
    "approval_inbox",
    "cleanup_policy_board",
    "rollback_burndown",
)

GOVERNANCE_FOLLOW_THROUGH_DIGEST_ALIAS_SPECS: Tuple[GovernanceLinkSpec, ...] = (
    (
        "entry_efficiency",
        "governance_review_handoff_acceptance_entry_efficiency",
    ),
    (
        "history",
        "governance_review_handoff_acceptance_follow_through_history",
    ),
    (
        "burndown",
        "governance_review_handoff_acceptance_follow_through_burndown",
    ),
)

GOVERNANCE_FOLLOW_THROUGH_BURNDOWN_ALIAS_SPECS: Tuple[GovernanceLinkSpec, ...] = (
    (
        "entry_efficiency",
        "governance_review_handoff_acceptance_entry_efficiency",
    ),
    (
        "history",
        "governance_review_handoff_acceptance_follow_through_history",
    ),
)

GOVERNANCE_FOLLOW_THROUGH_HISTORY_ALIAS_SPECS: Tuple[GovernanceLinkSpec, ...] = (
    (
        "entry_efficiency",
        "governance_review_handoff_acceptance_entry_efficiency",
    ),
    (
        "digest",
        "governance_review_handoff_acceptance_follow_through_digest",
    ),
    (
        "burndown",
        "governance_review_handoff_acceptance_follow_through_burndown",
    ),
)


def governance_discoverability_path(code: str) -> str:
    try:
        return GOVERNANCE_DISCOVERABILITY_PATHS[code]
    except KeyError as exc:
        raise ValueError(f"Unknown governance discoverability code: {code}") from exc


def build_governance_discoverability(
    self_code: str,
    *,
    include_export: bool = False,
    link_specs: Sequence[GovernanceLinkSpec] = (),
) -> Dict[str, str]:
    self_path = governance_discoverability_path(self_code)
    urls: Dict[str, str] = {"self": self_path}
    if include_export:
        urls["export"] = f"{self_path}/export?format=json"
    for spec in link_specs:
        if isinstance(spec, tuple):
            alias, code = spec
        else:
            alias = code = spec
        urls[alias] = governance_discoverability_path(code)
    return urls
