"""Tests for consumer row discoverability helpers."""
from __future__ import annotations

from yuantus.meta_engine.web.subcontracting_consumer_row_discoverability import (
    build_consumer_order_row_urls,
    build_message_owner_rebalance_age_row_urls,
    build_message_owner_rebalance_alert_summary_row_urls,
    build_message_owner_rebalance_batch_row_urls,
    build_message_owner_rebalance_latest_attempt_batch_urls,
    build_message_owner_rebalance_owner_row_urls,
    build_message_owner_rebalance_reason_row_urls,
    build_message_owner_rebalance_status_row_urls,
    build_message_owner_rebalance_trend_row_urls,
    build_message_owner_workload_owner_row_urls,
    build_message_owner_workload_scope_params,
    build_message_owner_workload_team_row_urls,
    build_message_owner_workload_vendor_row_urls,
    build_message_owner_workload_message_row_urls,
    build_receipt_analytics_row_urls,
    build_return_disposition_approval_inbox_row_urls,
    build_vendor_analytics_row_urls,
    build_vendor_message_board_row_urls,
    build_vendor_portal_order_row_urls,
)


def test_build_return_disposition_approval_inbox_row_urls_includes_board_and_assign():
    payload = build_return_disposition_approval_inbox_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        order_id="so-1",
        disposition_event_id="evt-1",
    )

    assert payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
        "approval_board": "/api/v1/subcontracting/orders/so-1/return-disposition-approval-board",
        "approval_assign": "/api/v1/subcontracting/orders/so-1/return-dispositions/evt-1/assign",
    }


def test_build_vendor_message_board_row_urls_includes_thread_link():
    payload = build_vendor_message_board_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        order_id="so-1",
    )

    assert payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
        "thread": "/api/v1/subcontracting/orders/so-1/vendor-messages",
    }


def test_build_consumer_order_row_urls_passthrough():
    payload = build_consumer_order_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
    )

    assert payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
    }


def test_build_message_owner_workload_message_row_urls_includes_scoped_links():
    payload = build_message_owner_workload_message_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        order_id="so-1",
        message_id="evt-1",
        workload_board_params={
            "vendor_id": "v-1",
            "owner": "planner-a",
            "include_closed": False,
            "include_paused": True,
            "message_limit": 200,
        },
        rebalance_preview_params={
            "vendor_id": "v-1",
            "message_ids": ["evt-2"],
            "max_moves": 5,
        },
        rebalance_history_params={
            "batch_id": "global-rebalance-1",
            "selection_mode": "message_ids",
        },
        rebalance_rollback_board_params={
            "batch_id": "global-rebalance-1",
            "strict_current_owner": True,
        },
    )

    assert payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
        "thread": "/api/v1/subcontracting/orders/so-1/vendor-messages",
        "workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board"
            "?vendor_id=v-1&owner=planner-a&include_closed=false&include_paused=true&message_limit=200"
        ),
        "rebalance_preview": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview"
            "?vendor_id=v-1&message_ids=evt-2&message_ids=evt-1&max_moves=5"
        ),
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?batch_id=global-rebalance-1&selection_mode=message_ids"
        ),
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?batch_id=global-rebalance-1&strict_current_owner=true"
        ),
    }


def test_build_vendor_portal_order_row_urls_includes_portal_workspace_and_workload_links():
    payload = build_vendor_portal_order_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        vendor_id="vendor-1",
        include_closed=True,
        timeline_limit=2,
    )

    assert payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
        "portal_board": (
            "/api/v1/subcontracting/vendors/vendor-1/portal-board"
            "?include_closed=true&timeline_limit=2"
        ),
        "workspace": (
            "/api/v1/subcontracting/vendors/vendor-1/workspace"
            "?include_closed=true&timeline_limit=2"
        ),
        "message_board": "/api/v1/subcontracting/vendors/vendor-1/message-board",
        "message_sla_board": (
            "/api/v1/subcontracting/vendors/vendor-1/message-board/sla-board"
        ),
        "message_owner_inbox": (
            "/api/v1/subcontracting/vendors/vendor-1/message-board/owner-inbox"
        ),
        "message_owner_workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board?vendor_id=vendor-1"
        ),
    }


def test_build_message_owner_workload_owner_team_and_vendor_row_urls_preserve_scope():
    scope_params = build_message_owner_workload_scope_params(
        vendor_id="vendor-1",
        owner="planner-a",
        team="ops",
        include_closed=False,
        include_paused=True,
        message_limit=50,
        owner_soft_limit=1,
        owner_hard_limit=2,
        aged_watch_hours=2,
        aged_breach_hours=8,
        pause_watch_hours=4,
        pause_breach_hours=12,
        sort_by="priority",
    )

    owner_payload = build_message_owner_workload_owner_row_urls(
        owner="planner-a",
        scope_params=scope_params,
    )
    team_payload = build_message_owner_workload_team_row_urls(
        team="ops",
        scope_params=scope_params,
    )
    vendor_payload = build_message_owner_workload_vendor_row_urls(
        vendor_id="vendor-1",
        scope_params=scope_params,
    )

    assert owner_payload == {
        "workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board"
            "?vendor_id=vendor-1&owner=planner-a&team=ops&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=1&owner_hard_limit=2&aged_watch_hours=2"
            "&aged_breach_hours=8&pause_watch_hours=4&pause_breach_hours=12&sort_by=priority"
        ),
        "rebalance_preview": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview"
            "?vendor_id=vendor-1&owner=planner-a&team=ops&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=1&owner_hard_limit=2&aged_watch_hours=2"
            "&aged_breach_hours=8&pause_watch_hours=4&pause_breach_hours=12&sort_by=priority"
        ),
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a"
        ),
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?vendor_id=vendor-1&from_owner=planner-a"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a"
        ),
    }
    assert team_payload == {
        "workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board"
            "?vendor_id=vendor-1&owner=planner-a&team=ops&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=1&owner_hard_limit=2&aged_watch_hours=2"
            "&aged_breach_hours=8&pause_watch_hours=4&pause_breach_hours=12&sort_by=priority"
        ),
        "rebalance_preview": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview"
            "?vendor_id=vendor-1&owner=planner-a&team=ops&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=1&owner_hard_limit=2&aged_watch_hours=2"
            "&aged_breach_hours=8&pause_watch_hours=4&pause_breach_hours=12&sort_by=priority"
        ),
    }
    assert vendor_payload == {
        "workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board"
            "?vendor_id=vendor-1&owner=planner-a&team=ops&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=1&owner_hard_limit=2&aged_watch_hours=2"
            "&aged_breach_hours=8&pause_watch_hours=4&pause_breach_hours=12&sort_by=priority"
        ),
        "rebalance_preview": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview"
            "?vendor_id=vendor-1&owner=planner-a&team=ops&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=1&owner_hard_limit=2&aged_watch_hours=2"
            "&aged_breach_hours=8&pause_watch_hours=4&pause_breach_hours=12&sort_by=priority"
        ),
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1"
        ),
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?vendor_id=vendor-1"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1"
        ),
        "message_board": "/api/v1/subcontracting/vendors/vendor-1/message-board",
        "message_sla_board": (
            "/api/v1/subcontracting/vendors/vendor-1/message-board/sla-board"
        ),
        "message_owner_inbox": (
            "/api/v1/subcontracting/vendors/vendor-1/message-board/owner-inbox"
        ),
        "portal_board": "/api/v1/subcontracting/vendors/vendor-1/portal-board",
        "workspace": "/api/v1/subcontracting/vendors/vendor-1/workspace",
        "execution_summary": "/api/v1/subcontracting/execution-summary?vendor_id=vendor-1",
        "execution_summary_export": (
            "/api/v1/subcontracting/execution-summary/export?format=json&vendor_id=vendor-1"
        ),
    }


def test_build_message_owner_rebalance_batch_row_urls_includes_history_and_rollback_links():
    payload = build_message_owner_rebalance_batch_row_urls(
        batch_id="global-rebalance-1",
        vendor_id="vendor-1",
        from_owner="planner-a",
        to_owner="planner-b",
        activity_date="2026-03-24",
        activity_kind="closed",
        activity_outcome="blocked_attempt",
        selection_mode="rollback",
        rollback_age_bucket="gte_72h",
        include_cross_vendor_only=True,
        strict_current_owner=False,
    )

    assert payload == {
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&activity_date=2026-03-24&activity_kind=closed&activity_outcome=blocked_attempt"
            "&selection_mode=rollback"
            "&include_cross_vendor_only=true&limit=200&sort_by=recent"
        ),
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=priority"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=priority"
        ),
    }


def test_build_message_owner_rebalance_reason_row_urls_includes_history_and_export_links():
    payload = build_message_owner_rebalance_reason_row_urls(
        rebalance_reason="rollback",
        vendor_id="vendor-1",
        from_owner="planner-a",
        to_owner="planner-b",
        activity_date="2026-03-24",
        activity_kind="closed",
        activity_outcome="blocked_attempt",
        selection_mode="rollback",
        include_cross_vendor_only=True,
    )

    assert payload == {
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b"
            "&activity_date=2026-03-24&activity_kind=closed&activity_outcome=blocked_attempt"
            "&selection_mode=rollback&rebalance_reason=rollback"
            "&include_cross_vendor_only=true&limit=200&sort_by=recent"
        ),
        "rebalance_history_export": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history/export"
            "?format=json&vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b"
            "&activity_date=2026-03-24&activity_kind=closed&activity_outcome=blocked_attempt"
            "&selection_mode=rollback&rebalance_reason=rollback"
            "&include_cross_vendor_only=true&limit=200&sort_by=recent"
        ),
    }


def test_build_message_owner_rebalance_status_row_urls_includes_board_and_burndown_links():
    payload = build_message_owner_rebalance_status_row_urls(
        rollback_status="assignment_drifted",
        vendor_id="vendor-1",
        from_owner="planner-a",
        to_owner="planner-b",
        batch_id="global-rebalance-1",
        rollback_age_bucket="gte_72h",
        include_cross_vendor_only=True,
        strict_current_owner=False,
        rollback_sort_by="status",
        burndown_sort_by="age",
        trend_days=21,
        forecast_window_days=10,
        on_call_owner="ops-oncall",
    )

    assert payload == {
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&rollback_status=assignment_drifted"
            "&include_cross_vendor_only=true&strict_current_owner=false&limit=200&sort_by=status"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&rollback_status=assignment_drifted"
            "&include_cross_vendor_only=true&strict_current_owner=false&limit=200&sort_by=age"
            "&trend_days=21&forecast_window_days=10&on_call_owner=ops-oncall&include_watch_alerts=true"
        ),
    }


def test_build_message_owner_rebalance_alert_summary_row_urls_includes_burndown_and_export_links():
    payload = build_message_owner_rebalance_alert_summary_row_urls(
        alert_scope="on_call",
        vendor_id="vendor-1",
        from_owner="planner-a",
        to_owner="planner-b",
        batch_id="global-rebalance-1",
        rollback_age_bucket="gte_72h",
        rollback_status="assignment_drifted",
        alert_level="critical",
        alert_execution_status="actionable",
        alert_latest_outcome_status="fully_blocked",
        include_cross_vendor_only=True,
        strict_current_owner=False,
        burndown_sort_by="age",
        trend_days=21,
        forecast_window_days=10,
        on_call_owner="ops-oncall",
        on_call_team="war-room",
        include_watch_alerts=False,
    )

    assert payload == {
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&rollback_status=assignment_drifted"
            "&alert_scope=on_call&alert_level=critical&alert_execution_status=actionable"
            "&alert_latest_outcome_status=fully_blocked&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=age&trend_days=21"
            "&forecast_window_days=10&on_call_owner=ops-oncall&on_call_team=war-room"
            "&include_watch_alerts=false"
        ),
        "rebalance_rollback_burndown_export": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown/export"
            "?format=json&vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&rollback_status=assignment_drifted"
            "&alert_scope=on_call&alert_level=critical&alert_execution_status=actionable"
            "&alert_latest_outcome_status=fully_blocked&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=age&trend_days=21"
            "&forecast_window_days=10&on_call_owner=ops-oncall&on_call_team=war-room"
            "&include_watch_alerts=false"
        ),
    }


def test_build_message_owner_rebalance_latest_attempt_batch_urls_preserves_source_context_and_attempt_history():
    payload = build_message_owner_rebalance_latest_attempt_batch_urls(
        source_batch_id="global-rebalance-1",
        attempt_batch_id="global-rebalance-rollback-1",
        vendor_id="vendor-1",
        source_from_owner="planner-a",
        source_to_owner="planner-b",
        attempt_from_owner="planner-b",
        attempt_to_owner="planner-a",
        attempt_activity_outcome="blocked_attempt",
        rollback_age_bucket="gte_72h",
        include_cross_vendor_only=True,
        strict_current_owner=False,
        rollback_sort_by="age",
    )

    assert payload == {
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-b&to_owner=planner-a&batch_id=global-rebalance-rollback-1"
            "&activity_kind=closed&activity_outcome=blocked_attempt&selection_mode=rollback"
            "&include_cross_vendor_only=true&limit=200&sort_by=recent"
        ),
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=age"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=age"
        ),
    }


def test_build_message_owner_rebalance_owner_row_urls_includes_workload_history_and_burndown_links():
    payload = build_message_owner_rebalance_owner_row_urls(
        owner="planner-a",
        vendor_id="vendor-1",
        to_owner="planner-b",
        rollback_age_bucket="gte_72h",
        include_cross_vendor_only=True,
        strict_current_owner=False,
        rollback_sort_by="status",
        burndown_sort_by="age",
        workload_scope_params=build_message_owner_workload_scope_params(
            vendor_id="vendor-1",
            include_closed=False,
            include_paused=True,
            message_limit=50,
            owner_soft_limit=2,
            owner_hard_limit=4,
            aged_watch_hours=3,
            aged_breach_hours=12,
            pause_watch_hours=6,
            pause_breach_hours=18,
            sort_by="priority",
        ),
    )

    assert payload == {
        "workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board"
            "?vendor_id=vendor-1&owner=planner-a&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=2&owner_hard_limit=4&aged_watch_hours=3"
            "&aged_breach_hours=12&pause_watch_hours=6&pause_breach_hours=18&sort_by=priority"
        ),
        "rebalance_preview": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview"
            "?vendor_id=vendor-1&owner=planner-a&include_closed=false&include_paused=true"
            "&message_limit=50&owner_soft_limit=2&owner_hard_limit=4&aged_watch_hours=3"
            "&aged_breach_hours=12&pause_watch_hours=6&pause_breach_hours=18&sort_by=priority"
        ),
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b"
            "&include_cross_vendor_only=true&limit=200&sort_by=recent"
        ),
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=status"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=200&sort_by=age"
            "&trend_days=14&forecast_window_days=7"
        ),
    }


def test_build_message_owner_rebalance_age_row_urls_includes_filtered_board_and_burndown_links():
    payload = build_message_owner_rebalance_age_row_urls(
        rollback_age_bucket="gte_72h",
        vendor_id="vendor-1",
        from_owner="planner-a",
        to_owner="planner-b",
        batch_id="global-rebalance-1",
        include_cross_vendor_only=True,
        strict_current_owner=False,
        limit=50,
        rollback_sort_by="status",
        burndown_sort_by="age",
        trend_days=21,
        forecast_window_days=10,
        on_call_owner="ops-oncall",
        on_call_team="war-room",
        include_watch_alerts=False,
    )

    assert payload == {
        "rebalance_rollback_board": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=50&sort_by=status"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=50&sort_by=age&trend_days=21"
            "&forecast_window_days=10&on_call_owner=ops-oncall&on_call_team=war-room"
            "&include_watch_alerts=false"
        ),
    }


def test_build_message_owner_rebalance_trend_row_urls_includes_day_scoped_history_and_burndown_links():
    payload = build_message_owner_rebalance_trend_row_urls(
        activity_date="2026-03-24",
        vendor_id="vendor-1",
        from_owner="planner-a",
        to_owner="planner-b",
        batch_id="global-rebalance-1",
        rollback_age_bucket="gte_72h",
        include_cross_vendor_only=True,
        strict_current_owner=False,
        limit=50,
        history_sort_by="owner",
        burndown_sort_by="age",
        trend_days=21,
        forecast_window_days=10,
        on_call_owner="ops-oncall",
        on_call_team="war-room",
        include_watch_alerts=False,
    )

    assert payload == {
        "rebalance_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&activity_date=2026-03-24&include_cross_vendor_only=true&limit=50&sort_by=owner"
        ),
        "opened_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&activity_date=2026-03-24&include_cross_vendor_only=true&limit=50&sort_by=owner"
            "&activity_kind=opened"
        ),
        "closed_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&activity_date=2026-03-24&include_cross_vendor_only=true&limit=50&sort_by=owner"
            "&activity_kind=closed"
        ),
        "rolled_back_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&activity_date=2026-03-24&include_cross_vendor_only=true&limit=50&sort_by=owner"
            "&activity_kind=closed&activity_outcome=applied"
        ),
        "blocked_close_attempts_history": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&activity_date=2026-03-24&include_cross_vendor_only=true&limit=50&sort_by=owner"
            "&activity_kind=closed&activity_outcome=blocked_attempt"
        ),
        "rebalance_rollback_burndown": (
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown"
            "?vendor_id=vendor-1&from_owner=planner-a&to_owner=planner-b&batch_id=global-rebalance-1"
            "&rollback_age_bucket=gte_72h&include_cross_vendor_only=true"
            "&strict_current_owner=false&limit=50&sort_by=age&trend_days=21"
            "&forecast_window_days=10&on_call_owner=ops-oncall&on_call_team=war-room"
            "&include_watch_alerts=false"
        ),
    }


def test_build_vendor_and_receipt_analytics_row_urls_include_consumer_and_vendor_links():
    vendor_payload = build_vendor_analytics_row_urls(vendor_id="vendor-1")
    receipt_payload = build_receipt_analytics_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        vendor_id="vendor-1",
    )
    receipt_without_vendor_payload = build_receipt_analytics_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        vendor_id=None,
    )

    assert vendor_payload == {
        "portal_board": "/api/v1/subcontracting/vendors/vendor-1/portal-board",
        "workspace": "/api/v1/subcontracting/vendors/vendor-1/workspace",
        "message_board": "/api/v1/subcontracting/vendors/vendor-1/message-board",
        "message_sla_board": "/api/v1/subcontracting/vendors/vendor-1/message-board/sla-board",
        "message_owner_inbox": "/api/v1/subcontracting/vendors/vendor-1/message-board/owner-inbox",
        "message_owner_workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board?vendor_id=vendor-1"
        ),
        "execution_summary": "/api/v1/subcontracting/execution-summary?vendor_id=vendor-1",
        "execution_summary_export": (
            "/api/v1/subcontracting/execution-summary/export?format=json&vendor_id=vendor-1"
        ),
    }
    assert receipt_payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
        "portal_board": "/api/v1/subcontracting/vendors/vendor-1/portal-board",
        "workspace": "/api/v1/subcontracting/vendors/vendor-1/workspace",
        "message_board": "/api/v1/subcontracting/vendors/vendor-1/message-board",
        "message_sla_board": "/api/v1/subcontracting/vendors/vendor-1/message-board/sla-board",
        "message_owner_inbox": "/api/v1/subcontracting/vendors/vendor-1/message-board/owner-inbox",
        "message_owner_workload_board": (
            "/api/v1/subcontracting/message-owner-workload-board?vendor_id=vendor-1"
        ),
        "vendor_analytics": "/api/v1/subcontracting/vendors/analytics",
    }
    assert receipt_without_vendor_payload == {
        "detail": "/api/v1/subcontracting/orders/so-1",
    }


def test_consumer_rollback_plane_closure_audit_scope_preservation():
    """Closure audit: all rollback row builders preserve supported scopes to correct targets."""

    # batch_row — rollback_board gets rollback scopes, history gets activity scopes
    batch = build_message_owner_rebalance_batch_row_urls(
        batch_id="batch-1",
        vendor_id="vendor-1",
        from_owner="owner-a",
        to_owner="owner-b",
        rollback_age_bucket="0_24h",
        rollback_status="pending",
        activity_date="2026-03-30",
        activity_kind="opened",
        selection_mode="batch_ids",
    )
    assert "batch_id=batch-1" in batch["rebalance_history"]
    assert "vendor_id=vendor-1" in batch["rebalance_history"]
    assert "activity_date=2026-03-30" in batch["rebalance_history"]
    assert "selection_mode=batch_ids" in batch["rebalance_history"]
    assert "rollback_age_bucket=0_24h" in batch["rebalance_rollback_board"]
    assert "rollback_status=pending" in batch["rebalance_rollback_board"]
    # history target doesn't support rollback_age_bucket
    assert "rollback_age_bucket" not in batch["rebalance_history"]
    # rollback_board target doesn't support activity_date
    assert "activity_date" not in batch["rebalance_rollback_board"]

    # status_row — board + burndown get rollback_status, burndown adds on_call
    status = build_message_owner_rebalance_status_row_urls(
        rollback_status="pending",
        vendor_id="vendor-1",
        from_owner="owner-a",
        on_call_owner="ops-oncall",
        on_call_team="ops-team",
    )
    assert "rollback_status=pending" in status["rebalance_rollback_board"]
    assert "rollback_status=pending" in status["rebalance_rollback_burndown"]
    assert "on_call_owner=ops-oncall" in status["rebalance_rollback_burndown"]
    assert "on_call_team=ops-team" in status["rebalance_rollback_burndown"]
    # board doesn't get on_call
    assert "on_call_owner" not in status["rebalance_rollback_board"]

    # age_row — board + burndown get rollback_age_bucket
    age = build_message_owner_rebalance_age_row_urls(
        rollback_age_bucket="24_72h",
        vendor_id="vendor-1",
        from_owner="owner-a",
        on_call_owner="ops-oncall",
    )
    assert "rollback_age_bucket=24_72h" in age["rebalance_rollback_board"]
    assert "rollback_age_bucket=24_72h" in age["rebalance_rollback_burndown"]
    assert "on_call_owner=ops-oncall" in age["rebalance_rollback_burndown"]

    # trend_row — history gets activity_date, burndown gets rollback scopes
    trend = build_message_owner_rebalance_trend_row_urls(
        activity_date="2026-03-30",
        vendor_id="vendor-1",
        from_owner="owner-a",
        rollback_age_bucket="0_24h",
        rollback_status="pending",
        on_call_owner="ops-oncall",
    )
    assert "activity_date=2026-03-30" in trend["rebalance_history"]
    assert "rollback_age_bucket=0_24h" in trend["rebalance_rollback_burndown"]
    assert "on_call_owner=ops-oncall" in trend["rebalance_rollback_burndown"]
    assert "activity_date=2026-03-30" in trend["opened_history"]
    assert "activity_kind=opened" in trend["opened_history"]
    assert "activity_kind=closed" in trend["closed_history"]

    # alert_summary_row — burndown gets alert scopes + on_call
    alert = build_message_owner_rebalance_alert_summary_row_urls(
        alert_scope="on_call",
        vendor_id="vendor-1",
        rollback_age_bucket="0_24h",
        rollback_status="pending",
        alert_level="breach",
        on_call_owner="ops-oncall",
        on_call_team="ops-team",
    )
    assert "alert_scope=on_call" in alert["rebalance_rollback_burndown"]
    assert "alert_level=breach" in alert["rebalance_rollback_burndown"]
    assert "rollback_age_bucket=0_24h" in alert["rebalance_rollback_burndown"]
    assert "on_call_owner=ops-oncall" in alert["rebalance_rollback_burndown"]
    assert "rebalance_rollback_burndown_export" in alert

    # owner_row — gets workload + history + rollback + burndown links
    owner = build_message_owner_rebalance_owner_row_urls(
        owner="owner-a",
        vendor_id="vendor-1",
        rollback_age_bucket="0_24h",
        rollback_status="pending",
    )
    assert "owner=owner-a" in owner["workload_board"]
    assert "from_owner=owner-a" in owner["rebalance_history"]
    assert "rollback_age_bucket=0_24h" in owner["rebalance_rollback_board"]
    assert "rollback_status=pending" in owner["rebalance_rollback_burndown"]

    # reason_row — history + export get rebalance_reason
    reason = build_message_owner_rebalance_reason_row_urls(
        rebalance_reason="owner_capacity",
        vendor_id="vendor-1",
        from_owner="owner-a",
        selection_mode="batch_ids",
    )
    assert "rebalance_reason=owner_capacity" in reason["rebalance_history"]
    assert "selection_mode=batch_ids" in reason["rebalance_history"]
    assert "rebalance_reason=owner_capacity" in reason["rebalance_history_export"]


def test_consumer_non_rollback_plane_closure_audit_scope_preservation():
    """Closure audit: all non-rollback consumer builders preserve supported scopes."""

    # vendor_portal_order_row_urls — vendor surfaces + workload
    portal = build_vendor_portal_order_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        vendor_id="vendor-1",
        include_closed=True,
        timeline_limit=5,
    )
    assert "vendor-1" in portal["portal_board"]
    assert "include_closed=true" in portal["portal_board"]
    assert "timeline_limit=5" in portal["portal_board"]
    assert "include_closed=true" in portal["workspace"]
    assert "vendor-1" in portal["message_board"]
    assert "vendor_id=vendor-1" in portal["message_owner_workload_board"]
    assert portal["detail"] == "/api/v1/subcontracting/orders/so-1"

    # workload_message_row_urls — consumer_urls + thread + conditional params
    scope = build_message_owner_workload_scope_params(
        vendor_id="vendor-1",
        owner="owner-a",
        sort_by="priority",
    )
    msg = build_message_owner_workload_message_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        order_id="so-1",
        message_id="msg-1",
        workload_board_params=scope,
        rebalance_preview_params=scope,
    )
    assert msg["thread"] == "/api/v1/subcontracting/orders/so-1/vendor-messages"
    assert "vendor_id=vendor-1" in msg["workload_board"]
    assert "owner=owner-a" in msg["workload_board"]
    assert "msg-1" in msg["rebalance_preview"]
    assert msg["detail"] == "/api/v1/subcontracting/orders/so-1"
    # no rebalance_history if params not provided
    assert "rebalance_history" not in msg

    # workload_owner_row_urls — scope_params preserved
    owner_urls = build_message_owner_workload_owner_row_urls(
        owner="owner-a",
        scope_params=scope,
    )
    assert "owner=owner-a" in owner_urls["workload_board"]
    assert "vendor_id=vendor-1" in owner_urls["workload_board"]
    assert "sort_by=priority" in owner_urls["workload_board"]
    assert "from_owner=owner-a" in owner_urls["rebalance_history"]

    # workload_team_row_urls — scope_params preserved
    team_urls = build_message_owner_workload_team_row_urls(
        team="ops-team",
        scope_params=scope,
    )
    assert "team=ops-team" in team_urls["workload_board"]
    assert "vendor_id=vendor-1" in team_urls["workload_board"]
    assert "team=ops-team" in team_urls["rebalance_preview"]

    # workload_vendor_row_urls — vendor surfaces + workload
    vendor_urls = build_message_owner_workload_vendor_row_urls(
        vendor_id="vendor-2",
        scope_params=scope,
    )
    assert "vendor_id=vendor-2" in vendor_urls["workload_board"]
    assert "vendor-2" in vendor_urls["portal_board"]
    assert "vendor-2" in vendor_urls["workspace"]
    assert "vendor-2" in vendor_urls["message_board"]
    assert "vendor_id=vendor-2" in vendor_urls["execution_summary"]
    assert "vendor_id=vendor-2" in vendor_urls["rebalance_history"]
    assert "vendor_id=vendor-2" in vendor_urls["rebalance_rollback_board"]
    assert "vendor_id=vendor-2" in vendor_urls["rebalance_rollback_burndown"]

    # vendor_analytics_row_urls — vendor_id in all targets
    analytics = build_vendor_analytics_row_urls(vendor_id="vendor-1")
    assert "vendor-1" in analytics["portal_board"]
    assert "vendor-1" in analytics["workspace"]
    assert "vendor-1" in analytics["message_board"]
    assert "vendor_id=vendor-1" in analytics["message_owner_workload_board"]
    assert "vendor_id=vendor-1" in analytics["execution_summary"]
    assert "vendor_id=vendor-1" in analytics["execution_summary_export"]

    # receipt_analytics_row_urls — consumer_urls + vendor surfaces
    receipt = build_receipt_analytics_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        vendor_id="vendor-1",
    )
    assert receipt["detail"] == "/api/v1/subcontracting/orders/so-1"
    assert "vendor-1" in receipt["portal_board"]
    assert "vendor_id=vendor-1" in receipt["message_owner_workload_board"]
    # without vendor_id, only consumer_urls
    receipt_no_vendor = build_receipt_analytics_row_urls(
        consumer_urls={"detail": "/api/v1/subcontracting/orders/so-1"},
        vendor_id=None,
    )
    assert receipt_no_vendor == {"detail": "/api/v1/subcontracting/orders/so-1"}
