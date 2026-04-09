"""Tests for governance router discoverability contracts."""
from __future__ import annotations

import pytest

from yuantus.meta_engine.web.subcontracting_governance_discoverability import (
    GOVERNANCE_FOLLOW_THROUGH_DIGEST_ALIAS_SPECS,
    GOVERNANCE_FOLLOW_THROUGH_HISTORY_ALIAS_SPECS,
    GOVERNANCE_REVIEW_DISCOVERABILITY_SPECS,
    GOVERNANCE_ROOT_DISCOVERABILITY_SPECS,
    build_governance_discoverability,
    governance_discoverability_path,
)
from yuantus.meta_engine.web.subcontracting_governance_row_discoverability import (
    build_governance_action_actor_row_urls,
    build_governance_action_batch_row_urls,
    build_governance_action_queue_summary_row_urls,
    build_governance_action_row_urls,
    build_governance_correlation_preset_row_urls,
    build_governance_preset_row_urls,
    build_governance_queue_row_urls,
    build_governance_review_handoff_ledger_snapshot_urls,
    build_governance_review_handoff_acceptance_digest_history_snapshot_urls,
    build_governance_review_handoff_follow_through_burndown_snapshot_urls,
    build_governance_review_handoff_follow_through_digest_history_snapshot_urls,
    build_governance_review_handoff_follow_through_digest_snapshot_urls,
    build_governance_review_handoff_acceptance_trends_snapshot_urls,
    build_governance_review_digest_burndown_snapshot_urls,
    build_governance_review_digest_history_snapshot_urls,
    build_governance_responsibility_actor_summary_row_urls,
    build_governance_responsibility_team_summary_row_urls,
    build_governance_review_handoff_acceptance_actor_row_urls,
    build_governance_review_handoff_acceptance_queue_row_urls,
    build_governance_review_handoff_acceptance_follow_through_batch_row_urls,
    build_governance_review_handoff_acceptance_follow_through_owner_row_urls,
    build_governance_review_handoff_acceptance_follow_through_view_row_urls,
    build_governance_review_handoff_acceptance_follow_through_trend_row_urls,
    build_governance_review_handoff_acceptance_follow_through_state_row_urls,
    build_governance_review_handoff_acceptance_follow_through_status_row_urls,
    build_governance_review_handoff_acceptance_entry_efficiency_row_urls,
    build_governance_review_handoff_acceptance_action_row_urls,
    build_governance_review_handoff_acceptance_status_row_urls,
    build_governance_review_handoff_acceptance_selection_mode_row_urls,
    build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls,
    build_governance_review_handoff_acceptance_trend_row_urls,
    build_governance_review_handoff_history_row_urls,
)


def test_build_governance_discoverability_root_aliases_include_entry_efficiency():
    payload = build_governance_discoverability(
        "governance_inbox",
        include_export=True,
        link_specs=GOVERNANCE_ROOT_DISCOVERABILITY_SPECS,
    )

    assert payload == {
        "self": "/api/v1/subcontracting/governance-inbox",
        "export": "/api/v1/subcontracting/governance-inbox/export?format=json",
        "action": "/api/v1/subcontracting/governance-inbox/action",
        "review_digest": "/api/v1/subcontracting/governance-inbox/review-digest",
        "review_handoff": "/api/v1/subcontracting/governance-inbox/review-handoff",
        "review_handoff_accept": "/api/v1/subcontracting/governance-inbox/review-handoff/accept",
        "review_handoff_history": "/api/v1/subcontracting/governance-inbox/review-handoff/history",
        "review_handoff_acceptance_digest": (
            "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-digest"
        ),
        "review_handoff_acceptance_entry_efficiency": (
            "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency"
        ),
        "review_handoff_acceptance_follow_through_digest": (
            "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest"
        ),
        "review_handoff_acceptance_follow_through_history": (
            "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-history"
        ),
        "review_handoff_acceptance_follow_through_burndown": (
            "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown"
        ),
        "review_handoff_acceptance_trends": (
            "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-trends"
        ),
        "presets": "/api/v1/subcontracting/governance-inbox/presets",
        "correlation_presets": "/api/v1/subcontracting/governance-inbox/correlation-presets",
        "burndown": "/api/v1/subcontracting/governance-inbox/burndown",
        "correlation_board": "/api/v1/subcontracting/governance-inbox/correlation-board",
        "sla_board": "/api/v1/subcontracting/governance-inbox/sla-board",
        "history": "/api/v1/subcontracting/governance-inbox/history",
        "approval_inbox": "/api/v1/subcontracting/return-disposition-approval-inbox",
        "cleanup_policy_board": (
            "/api/v1/subcontracting/approval-role-mappings/cleanup-policy-board"
        ),
        "rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
        ),
    }


def test_build_governance_discoverability_review_family_supports_follow_through_aliases():
    payload = build_governance_discoverability(
        "governance_review_handoff_acceptance_follow_through_digest",
        include_export=True,
        link_specs=(
            *GOVERNANCE_REVIEW_DISCOVERABILITY_SPECS,
            *GOVERNANCE_FOLLOW_THROUGH_DIGEST_ALIAS_SPECS,
        ),
    )

    assert payload["self"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest"
    )
    assert payload["export"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest/export?format=json"
    )
    assert payload["entry_efficiency"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency"
    )
    assert payload["history"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-history"
    )
    assert payload["burndown"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown"
    )
    assert payload["governance_review_handoff_acceptance_entry_efficiency"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency"
    )
    assert payload["governance_action"] == "/api/v1/subcontracting/governance-inbox/action"


def test_build_governance_discoverability_follow_through_history_supports_aliases():
    payload = build_governance_discoverability(
        "governance_review_handoff_acceptance_follow_through_history",
        include_export=True,
        link_specs=(
            *GOVERNANCE_REVIEW_DISCOVERABILITY_SPECS,
            *GOVERNANCE_FOLLOW_THROUGH_HISTORY_ALIAS_SPECS,
        ),
    )

    assert payload["self"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-history"
    )
    assert payload["digest"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest"
    )
    assert payload["burndown"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown"
    )
    assert payload["entry_efficiency"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency"
    )


def test_governance_discoverability_path_rejects_unknown_code():
    with pytest.raises(ValueError, match="Unknown governance discoverability code"):
        governance_discoverability_path("unknown")


def test_build_governance_queue_row_urls_supports_queue_specific_actions():
    payload = build_governance_queue_row_urls(
        queue_type="rollback_alert",
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        order_id="so-1",
    )

    assert payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
        "governance_action": "/api/v1/subcontracting/governance-inbox/action",
        "governance_burndown": "/api/v1/subcontracting/governance-inbox/burndown",
        "governance_correlation": "/api/v1/subcontracting/governance-inbox/correlation-board",
        "governance_sla_board": "/api/v1/subcontracting/governance-inbox/sla-board",
        "governance_history": "/api/v1/subcontracting/governance-inbox/history",
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


def test_build_governance_preset_row_urls_preserves_filters_and_export_contract():
    payload = build_governance_preset_row_urls(
        effective_filters={
            "responsible_actor": "qa-reviewer",
            "include_completed": False,
            "include_controlled": True,
            "actionable_only": False,
            "sort_by": "priority",
            "limit": 25,
        },
        preset_query={
            "preset_code": "my_governance_queue",
            "preview_limit": 25,
            "vendor_id": "vendor-1",
            "responsible_actor": "qa-reviewer",
            "responsible_team": "governance",
            "on_call_owner": "ops-oncall",
            "on_call_team": None,
        },
        preview_limit=25,
    )

    assert payload["governance_inbox"].startswith("/api/v1/subcontracting/governance-inbox?")
    assert "responsible_actor=qa-reviewer" in payload["governance_inbox"]
    assert payload["governance_export"].startswith(
        "/api/v1/subcontracting/governance-inbox/export?"
    )
    assert "format=json" in payload["governance_export"]
    assert payload["governance_review_handoff_history"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/history?"
    )
    assert payload["governance_review_handoff_accept"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/accept"
    )


def test_build_governance_review_digest_snapshot_urls_preserve_history_and_burndown_targets():
    history_payload = build_governance_review_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        queue_type="cleanup_debt",
        on_call_owner="ops-oncall",
        trend_days=10,
        forecast_window_days=5,
    )
    burndown_payload = build_governance_review_digest_burndown_snapshot_urls(
        vendor_id="vendor-1",
        queue_type="cleanup_debt",
        on_call_owner="ops-oncall",
        trend_days=10,
        forecast_window_days=5,
    )

    assert history_payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/history?"
    )
    assert "queue_type=cleanup_debt" in history_payload["self"]
    assert history_payload["export"].startswith(
        "/api/v1/subcontracting/governance-inbox/history/export?"
    )
    assert history_payload["burndown"].startswith(
        "/api/v1/subcontracting/governance-inbox/burndown?"
    )
    assert history_payload["primary_target"] == history_payload["self"]

    assert burndown_payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/burndown?"
    )
    assert "queue_type=cleanup_debt" in burndown_payload["self"]
    assert burndown_payload["export"].startswith(
        "/api/v1/subcontracting/governance-inbox/burndown/export?"
    )
    assert burndown_payload["history"].startswith(
        "/api/v1/subcontracting/governance-inbox/history?"
    )
    assert burndown_payload["primary_target"] == burndown_payload["self"]


def test_non_acceptance_governance_plane_closure_audit():
    """Closure audit: non-acceptance governance plane snapshot/row builders preserve supported scopes."""
    # review_digest_history_snapshot — carries vendor_id, queue_type, on_call_*
    rhs = build_governance_review_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        queue_type="rollback_alert",
        on_call_owner="ops-oncall",
        on_call_team="ops-team",
        trend_days=10,
        forecast_window_days=5,
    )
    assert "vendor_id=vendor-1" in rhs["self"]
    assert "queue_type=rollback_alert" in rhs["self"]
    assert "on_call_owner=ops-oncall" in rhs["self"]
    assert "on_call_team=ops-team" in rhs["self"]
    assert "vendor_id=vendor-1" in rhs["burndown"]
    assert "queue_type=rollback_alert" in rhs["burndown"]
    assert "on_call_owner=ops-oncall" in rhs["burndown"]
    assert "trend_days=10" in rhs["burndown"]
    # scopes NOT supported by governance_history/burndown targets
    assert "responsible_actor" not in rhs["self"]
    assert "responsible_team" not in rhs["self"]
    assert "preset_code" not in rhs["self"]

    # review_digest_burndown_snapshot — same scope set
    rbs = build_governance_review_digest_burndown_snapshot_urls(
        vendor_id="vendor-1",
        queue_type="cleanup_debt",
        on_call_owner="ops-oncall",
    )
    assert "queue_type=cleanup_debt" in rbs["self"]
    assert "queue_type=cleanup_debt" in rbs["history"]

    # governance_action_actor_row — carries actor + all action-level scopes
    actor_urls = build_governance_action_actor_row_urls(
        actor="ops-reviewer",
        vendor_id="vendor-1",
        queue_type="cleanup_debt",
        on_call_owner="ops-oncall",
    )
    assert "actor=ops-reviewer" in actor_urls["governance_history"]
    assert "vendor_id=vendor-1" in actor_urls["governance_history"]
    assert "queue_type=cleanup_debt" in actor_urls["governance_burndown"]

    # governance_action_queue_summary_row — carries queue + inbox scopes
    queue_urls = build_governance_action_queue_summary_row_urls(
        queue_type="rollback_alert",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
    )
    assert "queue_type=rollback_alert" in queue_urls["governance_inbox"]
    assert "responsible_actor=qa-reviewer" in queue_urls["governance_inbox"]
    assert "responsible_team=governance" in queue_urls["governance_correlation"]
    assert "queue_type=rollback_alert" in queue_urls["governance_history"]

    # responsibility_actor_summary_row — carries responsible_actor + inbox scopes
    resp_urls = build_governance_responsibility_actor_summary_row_urls(
        responsible_actor="qa-reviewer",
        vendor_id="vendor-1",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        actionable_only=True,
    )
    assert "responsible_actor=qa-reviewer" in resp_urls["governance_inbox"]
    assert "responsible_team=governance" in resp_urls["governance_inbox"]
    assert "actionable_only=true" in resp_urls["governance_inbox"]


def test_build_governance_review_family_history_snapshot_urls_preserve_surface_targets():
    acceptance_payload = build_governance_review_handoff_acceptance_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )
    follow_through_payload = (
        build_governance_review_handoff_follow_through_digest_history_snapshot_urls(
            vendor_id="vendor-1",
            responsible_actor="qa-reviewer",
            responsible_team="governance",
            on_call_owner="ops-oncall",
            preset_code="critical_triage",
            accepted_by="ops-oncall",
            selection_view_id="handoff-board",
            selection_mode="source_refs",
            follow_through_status="open_follow_through",
            open_only=True,
            activity_date="2026-03-24",
            activity_kind="opened",
            preview_limit=25,
            review_limit=10,
            handoff_limit=5,
            history_limit=8,
            trend_days=10,
            forecast_window_days=5,
            sort_by="priority",
        )
    )

    assert acceptance_payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/history?"
    )
    assert "accepted_by=ops-oncall" in acceptance_payload["self"]
    assert "action_batch_id=governance-action-1" in acceptance_payload["self"]
    assert acceptance_payload["acceptance_digest"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-digest?"
    )
    assert "action_batch_id=governance-action-1" in acceptance_payload["acceptance_digest"]
    assert acceptance_payload["acceptance_trends"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-trends?"
    )
    assert "action_batch_id=governance-action-1" in acceptance_payload["acceptance_trends"]
    assert acceptance_payload["primary_target"] == acceptance_payload["self"]

    assert follow_through_payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-history?"
    )
    assert "accepted_by=ops-oncall" in follow_through_payload["self"]
    assert "selection_mode=source_refs" in follow_through_payload["self"]
    assert "activity_date=2026-03-24" in follow_through_payload["self"]
    assert follow_through_payload["follow_through_digest"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest?"
    )
    assert "selection_mode=source_refs" in follow_through_payload["follow_through_digest"]
    assert follow_through_payload["follow_through_burndown"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown?"
    )
    assert "activity_date=2026-03-24" in follow_through_payload["follow_through_burndown"]
    assert follow_through_payload["primary_target"] == follow_through_payload["self"]


def test_build_governance_review_handoff_ledger_snapshot_urls_preserve_action_batch_scope():
    payload = build_governance_review_handoff_ledger_snapshot_urls(
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "action_batch_id=governance-action-1" in payload["review_handoff_history"]
    assert "action_batch_id=governance-action-1" in payload["acceptance_digest"]
    assert "action_batch_id=governance-action-1" in payload["acceptance_trends"]
    assert "action_batch_id=governance-action-1" in payload["follow_through_digest"]
    assert payload["primary_target"] == payload["self"]


def test_build_governance_review_handoff_follow_through_digest_snapshot_urls_preserve_digest_primary_target():
    payload = build_governance_review_handoff_follow_through_digest_snapshot_urls(
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        acceptance_status="accepted",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest?"
    )
    assert "accepted_by=ops-oncall" in payload["self"]
    assert "action_origin=review_handoff_acceptance" in payload["self"]
    assert "queue_type=cleanup_debt" in payload["self"]
    assert "selection_view_id=handoff-board" in payload["self"]
    assert "selection_mode=source_refs" in payload["self"]
    assert "follow_through_status=open_follow_through" in payload["self"]
    assert "acceptance_status=accepted" in payload["self"]
    assert "open_only=true" in payload["self"]
    assert "activity_date=2026-03-24" not in payload["self"]
    assert "activity_kind=opened" not in payload["self"]
    assert "selection_view_id=handoff-board" in payload["export"]
    assert "follow_through_status=open_follow_through" in payload["export"]
    assert "activity_date=2026-03-24" not in payload["export"]
    assert payload["follow_through_history"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-history?"
    )
    assert "selection_view_id=handoff-board" in payload["follow_through_history"]
    assert "action_origin=review_handoff_acceptance" in payload["follow_through_history"]
    assert "queue_type=cleanup_debt" in payload["follow_through_history"]
    assert "acceptance_status=accepted" in payload["follow_through_history"]
    assert "selection_view_id=handoff-board" in payload["follow_through_burndown"]
    assert "open_only=true" in payload["follow_through_burndown"]
    assert "acceptance_status=accepted" in payload["follow_through_burndown"]
    assert payload["acceptance_digest"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-digest?"
    )
    assert "selection_view_id=handoff-board" not in payload["acceptance_digest"]
    assert "open_only=true" not in payload["acceptance_digest"]
    assert "activity_date=2026-03-24" not in payload["acceptance_digest"]
    assert payload["acceptance_trends"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-trends?"
    )
    assert "acceptance_status=accepted" in payload["acceptance_trends"]
    assert "selection_view_id=handoff-board" not in payload["acceptance_trends"]
    assert "action_origin=review_handoff_acceptance" not in payload["acceptance_trends"]
    assert payload["entry_efficiency"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency?"
    )
    assert "acceptance_status=accepted" in payload["entry_efficiency"]
    assert "selection_view_id=handoff-board" in payload["entry_efficiency"]
    assert "action_origin=review_handoff_acceptance" in payload["entry_efficiency"]
    assert "queue_type=cleanup_debt" in payload["entry_efficiency"]
    assert "activity_date=2026-03-24" not in payload["entry_efficiency"]
    assert payload["review_digest"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-digest?"
    )
    assert "accepted_by=ops-oncall" not in payload["review_digest"]
    assert "selection_view_id=handoff-board" not in payload["review_digest"]


def test_build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls_preserve_supported_sibling_scopes():
    payload = build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls(
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        selection_view_id="handoff-board",
        selection_mode="mapping_ids",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency?"
    )
    assert "selection_view_id=handoff-board" in payload["self"]
    assert "action_origin=review_handoff_acceptance" in payload["self"]
    assert "queue_type=cleanup_debt" in payload["self"]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "action_origin=review_handoff_acceptance" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "queue_type=cleanup_debt" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "selection_view_id=handoff-board" not in payload["governance_review_digest"]
    assert "accepted_by=ops-oncall" not in payload["governance_review_digest"]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert payload["governance_review_handoff_acceptance_follow_through_burndown"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown?"
    )
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "selection_view_id=handoff-board" not in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert payload["primary_target"] == payload["self"]


def test_snapshot_urls_preserve_follow_through_state_scope():
    """history_snapshot and digest_snapshot URLs must carry follow_through_state to supported targets."""
    history_snap = build_governance_review_handoff_follow_through_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        preset_code="rollback_on_call",
        accepted_by="ops-oncall",
        follow_through_status="open_follow_through",
        follow_through_state="accepted_controlled_watch",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )
    # history_query targets get follow_through_state
    assert "follow_through_state=accepted_controlled_watch" in history_snap["self"]
    assert "follow_through_state=accepted_controlled_watch" in history_snap["export"]
    # burndown_query targets get follow_through_state
    assert "follow_through_state=accepted_controlled_watch" in history_snap[
        "follow_through_burndown"
    ]
    assert "follow_through_state=accepted_controlled_watch" in history_snap[
        "follow_through_burndown_export"
    ]
    # digest_query doesn't get follow_through_state (not supported by digest target)
    assert "follow_through_state" not in history_snap["follow_through_digest"]

    digest_snap = build_governance_review_handoff_follow_through_digest_snapshot_urls(
        vendor_id="vendor-1",
        preset_code="rollback_on_call",
        accepted_by="ops-oncall",
        follow_through_status="open_follow_through",
        follow_through_state="accepted_controlled_watch",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )
    # follow_through targets get follow_through_state
    assert "follow_through_state=accepted_controlled_watch" in digest_snap["self"]
    assert "follow_through_state=accepted_controlled_watch" in digest_snap["export"]
    assert "follow_through_state=accepted_controlled_watch" in digest_snap[
        "follow_through_history"
    ]
    assert "follow_through_state=accepted_controlled_watch" in digest_snap[
        "follow_through_burndown"
    ]
    assert "follow_through_state=accepted_controlled_watch" in digest_snap[
        "entry_efficiency"
    ]
    # acceptance_digest doesn't support follow_through_state
    assert "follow_through_state" not in digest_snap["acceptance_digest"]
    # review_digest doesn't support follow_through_state
    assert "follow_through_state" not in digest_snap["review_digest"]


def test_snapshot_urls_preserve_acceptance_action_scope():
    """All 5 snapshot URL builders must carry acceptance_action to supported targets."""
    # 1. acceptance_digest_history_snapshot
    adhs = build_governance_review_handoff_acceptance_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_action="acknowledge",
        accepted_by="ops-oncall",
    )
    assert "acceptance_action=acknowledge" in adhs["self"]
    assert "acceptance_action=acknowledge" in adhs["acceptance_digest"]
    assert "acceptance_action=acknowledge" in adhs["acceptance_trends"]

    # 2. follow_through_digest_history_snapshot
    fths = build_governance_review_handoff_follow_through_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_action="acknowledge",
        accepted_by="ops-oncall",
        follow_through_status="open_follow_through",
    )
    assert "acceptance_action=acknowledge" in fths["self"]
    assert "acceptance_action=acknowledge" in fths["follow_through_digest"]
    assert "acceptance_action=acknowledge" in fths["follow_through_burndown"]

    # 3. follow_through_digest_snapshot
    ftds = build_governance_review_handoff_follow_through_digest_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_action="acknowledge",
        accepted_by="ops-oncall",
        follow_through_status="open_follow_through",
    )
    assert "acceptance_action=acknowledge" in ftds["self"]
    assert "acceptance_action=acknowledge" in ftds["follow_through_history"]
    assert "acceptance_action=acknowledge" in ftds["follow_through_burndown"]
    assert "acceptance_action=acknowledge" in ftds["entry_efficiency"]
    assert "acceptance_action=acknowledge" in ftds["acceptance_digest"]
    assert "acceptance_action=acknowledge" in ftds["acceptance_trends"]
    # review_digest doesn't support acceptance_action
    assert "acceptance_action" not in ftds["review_digest"]

    # 4. acceptance_trends_snapshot
    ats = build_governance_review_handoff_acceptance_trends_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_action="acknowledge",
        accepted_by="ops-oncall",
    )
    assert "acceptance_action=acknowledge" in ats["self"]
    assert "acceptance_action=acknowledge" in ats["acceptance_digest"]

    # 5. entry_efficiency_snapshot
    ees = build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_action="acknowledge",
        accepted_by="ops-oncall",
        follow_through_status="open_follow_through",
    )
    assert "acceptance_action=acknowledge" in ees["self"]
    assert "acceptance_action=acknowledge" in ees["export"]
    assert "acceptance_action=acknowledge" in ees[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "acceptance_action=acknowledge" in ees[
        "governance_review_handoff_acceptance_trends"
    ]
    # review_digest doesn't support acceptance_action
    assert "acceptance_action" not in ees[
        "governance_review_digest"
    ]


def test_snapshot_urls_preserve_acceptance_status_scope():
    """All 5 snapshot URL builders must carry acceptance_status to supported targets."""
    # 1. acceptance_digest_history_snapshot
    adhs = build_governance_review_handoff_acceptance_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_status="accepted",
        accepted_by="ops-oncall",
    )
    assert "acceptance_status=accepted" in adhs["self"]
    assert "acceptance_status=accepted" in adhs["acceptance_digest"]
    assert "acceptance_status=accepted" in adhs["acceptance_trends"]

    # 2. follow_through_digest_history_snapshot
    fths = build_governance_review_handoff_follow_through_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_status="accepted",
        accepted_by="ops-oncall",
    )
    assert "acceptance_status=accepted" in fths["self"]
    assert "acceptance_status=accepted" in fths["follow_through_digest"]
    assert "acceptance_status=accepted" in fths["follow_through_burndown"]

    # 3. follow_through_digest_snapshot
    ftds = build_governance_review_handoff_follow_through_digest_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_status="accepted",
        accepted_by="ops-oncall",
    )
    assert "acceptance_status=accepted" in ftds["self"]
    assert "acceptance_status=accepted" in ftds["follow_through_history"]
    assert "acceptance_status=accepted" in ftds["follow_through_burndown"]
    assert "acceptance_status=accepted" in ftds["entry_efficiency"]
    assert "acceptance_status=accepted" in ftds["acceptance_digest"]
    assert "acceptance_status=accepted" in ftds["acceptance_trends"]
    assert "acceptance_status" not in ftds["review_digest"]

    # 4. acceptance_trends_snapshot
    ats = build_governance_review_handoff_acceptance_trends_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_status="accepted",
        accepted_by="ops-oncall",
    )
    assert "acceptance_status=accepted" in ats["self"]
    assert "acceptance_status=accepted" in ats["acceptance_digest"]

    # 5. entry_efficiency_snapshot
    ees = build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls(
        vendor_id="vendor-1",
        acceptance_status="accepted",
        accepted_by="ops-oncall",
    )
    assert "acceptance_status=accepted" in ees["self"]
    assert "acceptance_status=accepted" in ees["export"]
    assert "acceptance_status=accepted" in ees[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "acceptance_status=accepted" in ees[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "acceptance_status" not in ees["governance_review_digest"]


def test_snapshot_urls_preserve_selection_mode_scope():
    """Snapshot URL builders must carry selection_mode to targets that support it."""
    # follow_through_digest_history_snapshot — the only builder that had a gap
    fths = build_governance_review_handoff_follow_through_digest_history_snapshot_urls(
        vendor_id="vendor-1",
        selection_mode="source_refs",
        accepted_by="ops-oncall",
        follow_through_status="open_follow_through",
    )
    # self/export (history target) — supports selection_mode
    assert "selection_mode=source_refs" in fths["self"]
    assert "selection_mode=source_refs" in fths["export"]
    # digest target — supports selection_mode (was the gap, now fixed)
    assert "selection_mode=source_refs" in fths["follow_through_digest"]
    assert "selection_mode=source_refs" in fths["follow_through_digest_export"]
    # burndown target — supports selection_mode (was the gap, now fixed)
    assert "selection_mode=source_refs" in fths["follow_through_burndown"]
    assert "selection_mode=source_refs" in fths["follow_through_burndown_export"]

    # follow_through_digest_snapshot — already complete, verify
    ftds = build_governance_review_handoff_follow_through_digest_snapshot_urls(
        vendor_id="vendor-1",
        selection_mode="source_refs",
        accepted_by="ops-oncall",
    )
    assert "selection_mode=source_refs" in ftds["self"]
    assert "selection_mode=source_refs" in ftds["follow_through_history"]
    assert "selection_mode=source_refs" in ftds["follow_through_burndown"]
    assert "selection_mode=source_refs" in ftds["entry_efficiency"]
    # acceptance_digest doesn't support selection_mode
    assert "selection_mode" not in ftds["acceptance_digest"]
    # acceptance_trends doesn't support selection_mode
    assert "selection_mode" not in ftds["acceptance_trends"]

    # entry_efficiency_snapshot — already complete, verify
    ees = build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls(
        vendor_id="vendor-1",
        selection_mode="source_refs",
        accepted_by="ops-oncall",
    )
    assert "selection_mode=source_refs" in ees["self"]
    assert "selection_mode=source_refs" in ees[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    # acceptance_trends doesn't support selection_mode
    assert "selection_mode" not in ees[
        "governance_review_handoff_acceptance_trends"
    ]


def test_acceptance_plane_closure_audit_follow_through_state_on_remaining_snapshot_builders():
    """Closure audit: follow_through_state preserved on burndown_snapshot and entry_efficiency_snapshot."""
    # burndown_snapshot — all 3 targets support follow_through_state
    bs = build_governance_review_handoff_follow_through_burndown_snapshot_urls(
        vendor_id="vendor-1",
        follow_through_state="accepted_controlled_watch",
        accepted_by="ops-oncall",
    )
    assert "follow_through_state=accepted_controlled_watch" in bs["self"]
    assert "follow_through_state=accepted_controlled_watch" in bs["follow_through_history"]
    assert "follow_through_state=accepted_controlled_watch" in bs["follow_through_digest"]

    # entry_efficiency_snapshot — self + follow_through targets support it
    ees = build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls(
        vendor_id="vendor-1",
        follow_through_state="accepted_controlled_watch",
        accepted_by="ops-oncall",
    )
    assert "follow_through_state=accepted_controlled_watch" in ees["self"]
    assert "follow_through_state=accepted_controlled_watch" in ees[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "follow_through_state=accepted_controlled_watch" in ees[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "follow_through_state=accepted_controlled_watch" in ees[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    # targets that don't support follow_through_state
    assert "follow_through_state" not in ees[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "follow_through_state" not in ees[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "follow_through_state" not in ees["governance_review_digest"]


def test_build_governance_review_handoff_follow_through_burndown_snapshot_urls_preserve_burndown_primary_target():
    payload = build_governance_review_handoff_follow_through_burndown_snapshot_urls(
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        selection_view_id="handoff-board",
        selection_mode="mapping_ids",
        follow_through_status="open_follow_through",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        trend_days=10,
        forecast_window_days=5,
    )

    assert payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown?"
    )
    assert "activity_date=2026-03-24" in payload["self"]
    assert payload["follow_through_history"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-history?"
    )
    assert "activity_kind=opened" in payload["follow_through_history"]
    assert "selection_view_id=handoff-board" in payload["follow_through_history"]
    assert "selection_mode=mapping_ids" in payload["follow_through_history"]
    assert "action_origin=review_handoff_acceptance" in payload["follow_through_history"]
    assert "queue_type=cleanup_debt" in payload["follow_through_history"]
    assert "follow_through_status=open_follow_through" in payload["follow_through_digest"]
    assert "action_origin=review_handoff_acceptance" in payload["follow_through_digest"]
    assert "queue_type=cleanup_debt" in payload["follow_through_digest"]
    assert "open_only=true" in payload["self"]
    assert payload["follow_through_digest"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest?"
    )
    assert payload["primary_target"] == payload["self"]


def test_build_governance_review_handoff_acceptance_follow_through_view_row_urls_preserve_selection_view_scope():
    payload = build_governance_review_handoff_acceptance_follow_through_view_row_urls(
        selection_view_id="handoff-board",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-digest?"
    )


def test_build_governance_review_handoff_acceptance_follow_through_batch_row_urls_preserve_batch_scope():
    payload = build_governance_review_handoff_acceptance_follow_through_batch_row_urls(
        action_batch_id="governance-action-1",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]


def test_build_governance_review_handoff_acceptance_trends_snapshot_urls_preserve_trends_primary_target():
    payload = build_governance_review_handoff_acceptance_trends_snapshot_urls(
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        acceptance_action="acknowledge",
        acceptance_status="pending_acceptance",
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert payload["self"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-trends?"
    )
    assert "accepted_by=ops-oncall" in payload["self"]
    assert "action_batch_id=governance-action-1" in payload["self"]
    assert "acceptance_action=acknowledge" in payload["self"]
    assert "acceptance_status=pending_acceptance" in payload["self"]
    assert "activity_date=2026-03-24" in payload["self"]
    assert "activity_kind=opened" in payload["self"]
    assert "current_handoff_owner" not in payload["self"]
    assert payload["acceptance_digest"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-digest?"
    )
    assert "current_handoff_owner=ops-reviewer" in payload["acceptance_digest"]
    assert "action_batch_id=governance-action-1" in payload["acceptance_digest"]
    assert payload["history"].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/history?"
    )
    assert "current_handoff_owner=ops-reviewer" in payload["history"]
    assert "action_batch_id=governance-action-1" in payload["history"]
    assert payload["primary_target"] == payload["self"]


def test_build_governance_review_handoff_acceptance_status_row_urls_keep_status_scope():
    payload = build_governance_review_handoff_acceptance_status_row_urls(
        acceptance_status="pending_acceptance",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        acceptance_action="acknowledge",
        selection_view_id="handoff-board",
        selection_mode="mapping_ids",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "acceptance_status=pending_acceptance" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "acceptance_action=acknowledge" in payload[
        "governance_review_handoff_acceptance_trends_export"
    ]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "activity_date=2026-03-24" not in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "activity_kind=opened" not in payload[
        "governance_review_handoff_acceptance_digest_export"
    ]


def test_build_governance_review_history_row_urls_and_correlation_preset_rows_keep_scope():
    history_payload = build_governance_review_handoff_history_row_urls(
        handoff_query={
            "vendor_id": "vendor-1",
            "responsible_actor": "qa-reviewer",
            "responsible_team": "governance",
            "on_call_owner": "ops-oncall",
            "preset_code": "critical_triage",
            "preview_limit": 25,
            "review_limit": 10,
            "handoff_limit": 5,
            "trend_days": 10,
            "forecast_window_days": 5,
        },
        acceptance_scope_query={
            "vendor_id": "vendor-1",
            "responsible_actor": "qa-reviewer",
            "responsible_team": "governance",
            "on_call_owner": "ops-oncall",
            "current_handoff_owner": "ops-global",
            "preset_code": "critical_triage",
            "accepted_by": "ops-oncall",
            "preview_limit": 25,
            "review_limit": 10,
            "trend_days": 10,
            "forecast_window_days": 5,
            "selection_view_id": "handoff-board",
            "selection_mode": "source_refs",
            "follow_through_status": "open_follow_through",
            "open_only": True,
            "history_limit": 6,
            "handoff_limit": 5,
            "sort_by": "recent",
            "activity_date": "2026-03-24",
            "activity_kind": "opened",
        },
        digest_query={
            "vendor_id": "vendor-1",
            "responsible_actor": "qa-reviewer",
            "responsible_team": "governance",
            "on_call_owner": "ops-oncall",
            "current_handoff_owner": "ops-global",
            "preset_code": "critical_triage",
            "accepted_by": "ops-oncall",
            "preview_limit": 25,
            "review_limit": 10,
            "trend_days": 10,
            "forecast_window_days": 5,
        },
        history_query={
            "vendor_id": "vendor-1",
            "queue_type": "cleanup_debt",
            "source_ref": "map-1",
            "on_call_owner": "ops-oncall",
        },
        correlation_query={
            "vendor_id": "vendor-1",
            "queue_type": "cleanup_debt",
            "trend_days": 10,
            "forecast_window_days": 5,
        },
        history_limit=6,
        sort_by="recent",
    )
    preset_payload = build_governance_correlation_preset_row_urls(
        effective_filters={
            "include_completed": False,
            "include_controlled": False,
            "actionable_only": True,
            "include_watch_alerts": False,
            "sort_by": "priority",
            "limit": 25,
        },
        correlation_filters={
            "queue_type": "rollback_alert",
            "include_completed": False,
            "include_controlled": True,
            "actionable_only": False,
            "include_watch_alerts": False,
            "sort_by": "priority",
            "limit": 25,
        },
        preset_query={
            "preset_code": "critical_triage",
            "preview_limit": 25,
            "trend_days": 10,
            "forecast_window_days": 5,
            "vendor_id": "vendor-1",
            "responsible_actor": "qa-reviewer",
            "responsible_team": "governance",
            "on_call_owner": "ops-oncall",
        },
        preview_limit=25,
        trend_days=10,
        forecast_window_days=5,
    )

    assert "/acceptance-entry-efficiency" in history_payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "accepted_by=ops-oncall" in history_payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "activity_date=2026-03-24" in history_payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_kind=opened" in history_payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "sort_by=recent" in history_payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert preset_payload["governance_correlation_preset"].startswith(
        "/api/v1/subcontracting/governance-inbox/correlation-presets?"
    )
    assert "trend_days=10" in preset_payload["governance_correlation"]
    assert "forecast_window_days=5" in preset_payload["governance_burndown"]


def test_build_governance_action_summary_row_urls_keep_history_and_burndown_scope():
    actor_payload = build_governance_action_actor_row_urls(
        actor="ops-oncall",
        vendor_id="vendor-1",
        queue_type="rollback_alert",
        action="acknowledge",
        batch_id="governance-action-1",
        open_only=True,
        on_call_owner="ops-oncall",
        include_watch_alerts=True,
        limit=25,
        history_sort_by="recent",
        burndown_sort_by="recent",
        trend_days=10,
        forecast_window_days=5,
    )
    batch_payload = build_governance_action_batch_row_urls(
        batch_id="governance-action-1",
        vendor_id="vendor-1",
        queue_type="rollback_alert",
        action="acknowledge",
        actor="ops-oncall",
        open_only=True,
        on_call_owner="ops-oncall",
        include_watch_alerts=True,
        limit=25,
        history_sort_by="recent",
        burndown_sort_by="recent",
        trend_days=10,
        forecast_window_days=5,
    )
    action_payload = build_governance_action_row_urls(
        action="assign",
        vendor_id="vendor-1",
        queue_type="approval_debt",
        on_call_owner="ops-oncall",
        include_watch_alerts=True,
        limit=25,
        history_sort_by="recent",
        burndown_sort_by="recent",
        trend_days=10,
        forecast_window_days=5,
    )

    assert "actor=ops-oncall" in actor_payload["governance_history"]
    assert "open_only=true" in actor_payload["governance_history"]
    assert "actor=ops-oncall" in actor_payload["governance_burndown"]
    assert "trend_days=10" in actor_payload["governance_burndown"]
    assert "batch_id=governance-action-1" in batch_payload["governance_history"]
    assert "batch_id=governance-action-1" in batch_payload["governance_burndown"]
    assert "action=assign" in action_payload["governance_history"]
    assert "action=assign" in action_payload["governance_burndown_export"]


def test_build_governance_action_queue_summary_row_urls_adds_queue_analytics_links():
    payload = build_governance_action_queue_summary_row_urls(
        queue_type="rollback_alert",
        vendor_id="vendor-1",
        on_call_owner="ops-oncall",
        include_watch_alerts=True,
        limit=25,
        history_sort_by="recent",
        burndown_sort_by="recent",
        trend_days=10,
        forecast_window_days=5,
    )

    assert "queue_type=rollback_alert" in payload["governance_inbox"]
    assert "format=json" in payload["governance_inbox_export"]
    assert "queue_type=rollback_alert" in payload["governance_correlation"]
    assert "queue_type=rollback_alert" in payload["governance_sla_board"]
    assert "queue_type=rollback_alert" in payload["governance_history"]
    assert "queue_type=rollback_alert" in payload["governance_burndown"]


def test_build_governance_action_queue_summary_row_urls_preserves_responsibility_scope():
    payload = build_governance_action_queue_summary_row_urls(
        queue_type="cleanup_debt",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        include_watch_alerts=True,
        limit=25,
        history_sort_by="recent",
        burndown_sort_by="recent",
        trend_days=10,
        forecast_window_days=5,
    )

    assert "responsible_actor=qa-reviewer" in payload["governance_inbox"]
    assert "responsible_team=governance" in payload["governance_correlation"]
    assert "queue_type=cleanup_debt" in payload["governance_sla_board"]


def test_build_governance_review_handoff_acceptance_entry_efficiency_row_urls_keep_origin_scope():
    payload = build_governance_review_handoff_acceptance_entry_efficiency_row_urls(
        vendor_id="vendor-1",
        on_call_owner="ops-oncall",
        preset_code="rollback_on_call",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="recent",
    )

    assert payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ].startswith(
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency?"
    )
    assert "action_origin=review_handoff_acceptance" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "queue_type=cleanup_debt" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]
    assert "format=json" in payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]


def test_build_governance_review_handoff_acceptance_action_row_urls_keep_action_scope():
    payload = build_governance_review_handoff_acceptance_action_row_urls(
        acceptance_action="acknowledge",
        vendor_id="vendor-1",
        on_call_owner="ops-oncall",
        preset_code="rollback_on_call",
        accepted_by="ops-oncall",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="recent",
    )

    assert "acceptance_action=acknowledge" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_kind=opened" in payload[
        "governance_review_handoff_acceptance_follow_through_history_export"
    ]
    assert "queue_type=cleanup_debt" in payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]


def test_build_governance_review_handoff_acceptance_follow_through_status_row_urls_keep_status_scope():
    payload = build_governance_review_handoff_acceptance_follow_through_status_row_urls(
        follow_through_status="open_follow_through",
        vendor_id="vendor-1",
        on_call_owner="ops-oncall",
        preset_code="rollback_on_call",
        accepted_by="ops-oncall",
        acceptance_action="acknowledge",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="recent",
    )

    assert "follow_through_status=open_follow_through" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "acceptance_action=acknowledge" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_kind=opened" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown_export"
    ]
    assert "queue_type=cleanup_debt" in payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]


def test_build_governance_review_handoff_acceptance_follow_through_state_row_urls_keep_state_scope():
    payload = build_governance_review_handoff_acceptance_follow_through_state_row_urls(
        follow_through_state="accepted_controlled_watch",
        vendor_id="vendor-1",
        on_call_owner="ops-oncall",
        preset_code="rollback_on_call",
        accepted_by="ops-oncall",
        acceptance_action="acknowledge",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="recent",
    )

    assert "follow_through_state=accepted_controlled_watch" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "follow_through_status=open_follow_through" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "acceptance_action=acknowledge" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown_export"
    ]
    assert "queue_type=cleanup_debt" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "follow_through_state=accepted_controlled_watch" in payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]
    # activity_date/kind stripped from entry_efficiency targets
    assert "activity_date" not in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]


def test_pre_existing_row_builders_propagate_follow_through_state():
    """Pre-existing row builders must carry follow_through_state to supported targets."""
    # queue_row_urls — targets include follow_through_* and entry_efficiency
    queue = build_governance_review_handoff_acceptance_queue_row_urls(
        queue_type="cleanup_debt",
        follow_through_state="accepted_controlled_watch",
        accepted_by="ops-oncall",
    )
    assert "follow_through_state=accepted_controlled_watch" in queue[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "follow_through_state=accepted_controlled_watch" in queue[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    # trends/digest targets don't support follow_through_state
    assert "follow_through_state" not in queue[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "follow_through_state" not in queue[
        "governance_review_handoff_acceptance_digest"
    ]

    # selection_mode_row_urls
    sel = build_governance_review_handoff_acceptance_selection_mode_row_urls(
        selection_mode="source_refs",
        follow_through_state="accepted_monitor",
        accepted_by="ops-oncall",
    )
    assert "follow_through_state=accepted_monitor" in sel[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "follow_through_state=accepted_monitor" in sel[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]

    # follow_through_status_row_urls
    fts = build_governance_review_handoff_acceptance_follow_through_status_row_urls(
        follow_through_status="open_follow_through",
        follow_through_state="accepted_carry_forward",
        accepted_by="ops-oncall",
    )
    assert "follow_through_state=accepted_carry_forward" in fts[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "follow_through_state=accepted_carry_forward" in fts[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]

    # acceptance_status_row_urls — targets are trends/digest, neither supports state
    sts = build_governance_review_handoff_acceptance_status_row_urls(
        acceptance_status="accepted",
        follow_through_state="accepted_controlled_watch",
        accepted_by="ops-oncall",
    )
    assert "follow_through_state" not in sts[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "follow_through_state" not in sts[
        "governance_review_handoff_acceptance_digest"
    ]

    # entry_efficiency_row_urls — targets are entry_efficiency self/export
    eff = build_governance_review_handoff_acceptance_entry_efficiency_row_urls(
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        follow_through_state="accepted_follow_through",
        accepted_by="ops-oncall",
        acceptance_status="accepted",
    )
    assert "follow_through_state=accepted_follow_through" in eff[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "follow_through_state=accepted_follow_through" in eff[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]


def test_build_governance_review_handoff_acceptance_follow_through_owner_row_urls_keep_owner_scope():
    payload = build_governance_review_handoff_acceptance_follow_through_owner_row_urls(
        current_handoff_owner="ops-reviewer",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_team="governance",
        preset_code="critical_triage",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "current_handoff_owner=ops-reviewer" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "current_handoff_team=governance" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_kind=opened" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "format=json" in payload[
        "governance_review_handoff_acceptance_follow_through_digest_export"
    ]
    assert "current_handoff_owner=ops-reviewer" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]


def test_build_governance_review_handoff_acceptance_actor_row_urls_keep_actor_scope():
    payload = build_governance_review_handoff_acceptance_actor_row_urls(
        accepted_by="ops-oncall",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        action_batch_id="governance-action-1",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "accepted_by=ops-oncall" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "accepted_by=ops-oncall" in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "current_handoff_owner=ops-reviewer" in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_kind=opened" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "follow_through_status=open_follow_through" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "action_origin=review_handoff_acceptance" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "format=json" in payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]


def test_build_governance_review_handoff_acceptance_queue_row_urls_keep_batch_follow_through_scope():
    payload = build_governance_review_handoff_acceptance_queue_row_urls(
        queue_type="cleanup_debt",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "queue_type=cleanup_debt" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "accepted_by=ops-oncall" in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "current_handoff_owner=ops-reviewer" in payload[
        "governance_review_handoff_acceptance_digest"
    ]
    assert "selection_view_id=handoff-board" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "queue_type=cleanup_debt" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "format=json" in payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]


def test_build_governance_review_handoff_acceptance_selection_mode_row_urls_keep_follow_through_scope():
    payload = build_governance_review_handoff_acceptance_selection_mode_row_urls(
        selection_mode="mapping_ids",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        current_handoff_owner="ops-reviewer",
        current_handoff_team="governance",
        preset_code="critical_triage",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        acceptance_action="acknowledge",
        selection_view_id="handoff-board",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        activity_date="2026-03-24",
        activity_kind="opened",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "selection_mode=mapping_ids" in payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "acceptance_action=acknowledge" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_history"
    ]
    assert "activity_kind=opened" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown_export"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]


def test_build_governance_review_handoff_acceptance_trend_row_urls_keep_day_scope():
    payload = build_governance_review_handoff_acceptance_trend_row_urls(
        activity_date="2026-03-24",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        accepted_by="ops-oncall",
        action_batch_id="governance-action-1",
        preset_code="critical_triage",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "accepted_by=ops-oncall" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "action_batch_id=governance-action-1" in payload[
        "governance_review_handoff_acceptance_trends"
    ]
    assert "activity_kind=opened" in payload[
        "governance_review_handoff_acceptance_trends_opened"
    ]
    assert "activity_kind=accepted" in payload[
        "governance_review_handoff_acceptance_trends_accepted"
    ]
    assert "format=json" in payload[
        "governance_review_handoff_acceptance_trends_export"
    ]


def test_build_governance_review_handoff_follow_through_trend_row_urls_keep_day_scope():
    payload = build_governance_review_handoff_acceptance_follow_through_trend_row_urls(
        activity_date="2026-03-24",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        accepted_by="ops-oncall",
        preset_code="critical_triage",
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "activity_date=2026-03-24" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "accepted_by=ops-oncall" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown"
    ]
    assert "activity_kind=opened" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown_opened"
    ]
    assert "activity_kind=closed" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown_closed"
    ]
    assert "format=json" in payload[
        "governance_review_handoff_acceptance_follow_through_burndown_export"
    ]


def test_build_governance_review_handoff_acceptance_nested_row_urls_keep_actor_scope():
    owner_payload = (
        build_governance_review_handoff_acceptance_follow_through_owner_row_urls(
            current_handoff_owner="ops-reviewer",
            vendor_id="vendor-1",
            responsible_actor="qa-reviewer",
            responsible_team="governance",
            on_call_owner="ops-oncall",
            accepted_by="ops-oncall",
            preset_code="critical_triage",
            preview_limit=25,
            review_limit=10,
            handoff_limit=5,
            history_limit=8,
            trend_days=10,
            forecast_window_days=5,
            sort_by="priority",
        )
    )
    entry_payload = build_governance_review_handoff_acceptance_entry_efficiency_row_urls(
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        responsible_team="governance",
        on_call_owner="ops-oncall",
        accepted_by="ops-oncall",
        preset_code="critical_triage",
        selection_view_id="handoff-board",
        selection_mode="source_refs",
        follow_through_status="open_follow_through",
        action_origin="review_handoff_acceptance",
        queue_type="cleanup_debt",
        open_only=True,
        preview_limit=25,
        review_limit=10,
        handoff_limit=5,
        history_limit=8,
        trend_days=10,
        forecast_window_days=5,
        sort_by="priority",
    )

    assert "accepted_by=ops-oncall" in owner_payload[
        "governance_review_handoff_acceptance_follow_through_digest"
    ]
    assert "accepted_by=ops-oncall" in owner_payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "accepted_by=ops-oncall" in entry_payload[
        "governance_review_handoff_acceptance_entry_efficiency"
    ]
    assert "accepted_by=ops-oncall" in entry_payload[
        "governance_review_handoff_acceptance_entry_efficiency_export"
    ]


def test_build_governance_responsibility_actor_summary_row_urls_keep_actor_scope():
    payload = build_governance_responsibility_actor_summary_row_urls(
        responsible_actor="qa-reviewer",
        vendor_id="vendor-1",
        responsible_team="governance",
        queue_type="rollback_alert",
        on_call_owner="ops-oncall",
        limit=25,
        correlation_sort_by="priority",
        trend_days=10,
        forecast_window_days=5,
    )

    assert "responsible_actor=qa-reviewer" in payload["governance_inbox"]
    assert "responsible_team=governance" in payload["governance_inbox"]
    assert "queue_type=rollback_alert" in payload["governance_correlation"]
    assert "trend_days=10" in payload["governance_correlation"]
    assert "action_watch_hours=24" in payload["governance_correlation"]
    assert payload["governance_sla_board_export"].startswith(
        "/api/v1/subcontracting/governance-inbox/sla-board/export?format=json"
    )


def test_build_governance_responsibility_team_summary_row_urls_keep_team_scope():
    payload = build_governance_responsibility_team_summary_row_urls(
        responsible_team="governance",
        vendor_id="vendor-1",
        responsible_actor="qa-reviewer",
        queue_type="rollback_alert",
        include_completed=True,
        include_controlled=False,
        actionable_only=True,
        on_call_owner="ops-oncall",
        limit=25,
        correlation_sort_by="priority",
        trend_days=10,
        forecast_window_days=5,
    )

    assert "responsible_team=governance" in payload["governance_inbox"]
    assert "responsible_actor=qa-reviewer" in payload["governance_inbox"]
    assert "include_completed=true" in payload["governance_inbox"]
    assert "include_controlled=false" in payload["governance_correlation"]
    assert "actionable_only=true" in payload["governance_sla_board"]
    assert payload["governance_inbox_export"].startswith(
        "/api/v1/subcontracting/governance-inbox/export?format=json"
    )
