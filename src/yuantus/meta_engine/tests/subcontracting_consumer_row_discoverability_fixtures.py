"""Shared fixtures for consumer row discoverability contracts."""
from __future__ import annotations

from typing import Dict, Optional

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


def build_return_disposition_approval_inbox_row_urls_bundle(
    *,
    consumer_urls: Dict[str, str],
    order_id: str = "so-1",
    disposition_event_id: Optional[str] = "evt-1",
) -> Dict[str, str]:
    return build_return_disposition_approval_inbox_row_urls(
        consumer_urls=consumer_urls,
        order_id=order_id,
        disposition_event_id=disposition_event_id,
    )


def build_vendor_message_board_row_urls_bundle(
    *,
    consumer_urls: Dict[str, str],
    order_id: str = "so-1",
) -> Dict[str, str]:
    return build_vendor_message_board_row_urls(
        consumer_urls=consumer_urls,
        order_id=order_id,
    )


def build_consumer_order_row_urls_bundle(
    *,
    consumer_urls: Dict[str, str],
) -> Dict[str, str]:
    return build_consumer_order_row_urls(consumer_urls=consumer_urls)


def build_vendor_portal_order_row_urls_bundle(
    *,
    consumer_urls: Dict[str, str],
    vendor_id: str = "vendor-1",
    include_closed: bool = False,
    timeline_limit: int = 3,
) -> Dict[str, str]:
    return build_vendor_portal_order_row_urls(
        consumer_urls=consumer_urls,
        vendor_id=vendor_id,
        include_closed=include_closed,
        timeline_limit=timeline_limit,
    )


def build_message_owner_workload_scope_params_bundle(
    *,
    vendor_id: Optional[str] = None,
    owner: Optional[str] = None,
    team: Optional[str] = None,
    include_closed: bool = False,
    include_paused: bool = True,
    message_limit: int = 200,
    owner_soft_limit: int = 3,
    owner_hard_limit: int = 6,
    aged_watch_hours: int = 4,
    aged_breach_hours: int = 24,
    pause_watch_hours: int = 12,
    pause_breach_hours: int = 48,
    sort_by: str = "priority",
) -> Dict[str, object]:
    return build_message_owner_workload_scope_params(
        vendor_id=vendor_id,
        owner=owner,
        team=team,
        include_closed=include_closed,
        include_paused=include_paused,
        message_limit=message_limit,
        owner_soft_limit=owner_soft_limit,
        owner_hard_limit=owner_hard_limit,
        aged_watch_hours=aged_watch_hours,
        aged_breach_hours=aged_breach_hours,
        pause_watch_hours=pause_watch_hours,
        pause_breach_hours=pause_breach_hours,
        sort_by=sort_by,
    )


def build_message_owner_workload_owner_row_urls_bundle(
    *,
    owner: str = "planner-a",
    scope_params: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    return build_message_owner_workload_owner_row_urls(
        owner=owner,
        scope_params=scope_params or build_message_owner_workload_scope_params_bundle(),
    )


def build_message_owner_workload_team_row_urls_bundle(
    *,
    team: str = "ops",
    scope_params: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    return build_message_owner_workload_team_row_urls(
        team=team,
        scope_params=scope_params or build_message_owner_workload_scope_params_bundle(),
    )


def build_message_owner_workload_vendor_row_urls_bundle(
    *,
    vendor_id: str = "vendor-1",
    scope_params: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    return build_message_owner_workload_vendor_row_urls(
        vendor_id=vendor_id,
        scope_params=scope_params or build_message_owner_workload_scope_params_bundle(),
    )


def build_message_owner_workload_message_row_urls_bundle(
    *,
    consumer_urls: Dict[str, str],
    order_id: str = "so-1",
    message_id: Optional[str] = "evt-1",
    workload_board_params: Optional[Dict[str, object]] = None,
    rebalance_preview_params: Optional[Dict[str, object]] = None,
    rebalance_history_params: Optional[Dict[str, object]] = None,
    rebalance_rollback_board_params: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    return build_message_owner_workload_message_row_urls(
        consumer_urls=consumer_urls,
        order_id=order_id,
        message_id=message_id,
        workload_board_params=workload_board_params,
        rebalance_preview_params=rebalance_preview_params,
        rebalance_history_params=rebalance_history_params,
        rebalance_rollback_board_params=rebalance_rollback_board_params,
    )


def build_message_owner_rebalance_batch_row_urls_bundle(
    *,
    batch_id: str = "global-rebalance-1",
    vendor_id: Optional[str] = None,
    from_owner: Optional[str] = None,
    to_owner: Optional[str] = None,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    activity_outcome: Optional[str] = None,
    selection_mode: Optional[str] = None,
    rollback_age_bucket: Optional[str] = None,
    rollback_status: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    strict_current_owner: bool = True,
    history_limit: int = 200,
    history_sort_by: str = "recent",
    rollback_sort_by: str = "priority",
) -> Dict[str, str]:
    return build_message_owner_rebalance_batch_row_urls(
        batch_id=batch_id,
        vendor_id=vendor_id,
        from_owner=from_owner,
        to_owner=to_owner,
        activity_date=activity_date,
        activity_kind=activity_kind,
        activity_outcome=activity_outcome,
        selection_mode=selection_mode,
        rollback_age_bucket=rollback_age_bucket,
        rollback_status=rollback_status,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        history_limit=history_limit,
        history_sort_by=history_sort_by,
        rollback_sort_by=rollback_sort_by,
    )


def build_message_owner_rebalance_latest_attempt_batch_urls_bundle(
    *,
    source_batch_id: str = "global-rebalance-1",
    attempt_batch_id: str = "global-rebalance-rollback-1",
    vendor_id: Optional[str] = None,
    source_from_owner: Optional[str] = None,
    source_to_owner: Optional[str] = None,
    attempt_from_owner: Optional[str] = None,
    attempt_to_owner: Optional[str] = None,
    attempt_activity_outcome: Optional[str] = None,
    rollback_age_bucket: Optional[str] = None,
    rollback_status: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    strict_current_owner: bool = True,
    history_limit: int = 200,
    history_sort_by: str = "recent",
    rollback_sort_by: str = "priority",
) -> Dict[str, str]:
    return build_message_owner_rebalance_latest_attempt_batch_urls(
        source_batch_id=source_batch_id,
        attempt_batch_id=attempt_batch_id,
        vendor_id=vendor_id,
        source_from_owner=source_from_owner,
        source_to_owner=source_to_owner,
        attempt_from_owner=attempt_from_owner,
        attempt_to_owner=attempt_to_owner,
        attempt_activity_outcome=attempt_activity_outcome,
        rollback_age_bucket=rollback_age_bucket,
        rollback_status=rollback_status,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        history_limit=history_limit,
        history_sort_by=history_sort_by,
        rollback_sort_by=rollback_sort_by,
    )


def build_message_owner_rebalance_reason_row_urls_bundle(
    *,
    rebalance_reason: str = "aged_queue",
    vendor_id: Optional[str] = None,
    from_owner: Optional[str] = None,
    to_owner: Optional[str] = None,
    batch_id: Optional[str] = None,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    activity_outcome: Optional[str] = None,
    selection_mode: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    limit: int = 200,
    history_sort_by: str = "recent",
) -> Dict[str, str]:
    return build_message_owner_rebalance_reason_row_urls(
        rebalance_reason=rebalance_reason,
        vendor_id=vendor_id,
        from_owner=from_owner,
        to_owner=to_owner,
        batch_id=batch_id,
        activity_date=activity_date,
        activity_kind=activity_kind,
        activity_outcome=activity_outcome,
        selection_mode=selection_mode,
        include_cross_vendor_only=include_cross_vendor_only,
        limit=limit,
        history_sort_by=history_sort_by,
    )


def build_message_owner_rebalance_owner_row_urls_bundle(
    *,
    owner: str = "planner-a",
    vendor_id: Optional[str] = None,
    to_owner: Optional[str] = None,
    rollback_age_bucket: Optional[str] = None,
    rollback_status: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    strict_current_owner: bool = True,
    history_limit: int = 200,
    history_sort_by: str = "recent",
    rollback_sort_by: str = "priority",
    burndown_sort_by: str = "age",
    workload_scope_params: Optional[Dict[str, object]] = None,
) -> Dict[str, str]:
    return build_message_owner_rebalance_owner_row_urls(
        owner=owner,
        vendor_id=vendor_id,
        to_owner=to_owner,
        rollback_age_bucket=rollback_age_bucket,
        rollback_status=rollback_status,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        history_limit=history_limit,
        history_sort_by=history_sort_by,
        rollback_sort_by=rollback_sort_by,
        burndown_sort_by=burndown_sort_by,
        workload_scope_params=workload_scope_params,
    )


def build_message_owner_rebalance_age_row_urls_bundle(
    *,
    rollback_age_bucket: str = "gte_72h",
    vendor_id: Optional[str] = None,
    from_owner: Optional[str] = None,
    to_owner: Optional[str] = None,
    batch_id: Optional[str] = None,
    rollback_status: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    strict_current_owner: bool = True,
    limit: int = 200,
    rollback_sort_by: str = "priority",
    burndown_sort_by: str = "age",
    trend_days: int = 14,
    forecast_window_days: int = 7,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
) -> Dict[str, str]:
    return build_message_owner_rebalance_age_row_urls(
        rollback_age_bucket=rollback_age_bucket,
        vendor_id=vendor_id,
        from_owner=from_owner,
        to_owner=to_owner,
        batch_id=batch_id,
        rollback_status=rollback_status,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        limit=limit,
        rollback_sort_by=rollback_sort_by,
        burndown_sort_by=burndown_sort_by,
        trend_days=trend_days,
        forecast_window_days=forecast_window_days,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
    )


def build_message_owner_rebalance_trend_row_urls_bundle(
    *,
    activity_date: str = "2026-03-24",
    vendor_id: Optional[str] = None,
    from_owner: Optional[str] = None,
    to_owner: Optional[str] = None,
    batch_id: Optional[str] = None,
    rollback_age_bucket: Optional[str] = None,
    rollback_status: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    strict_current_owner: bool = True,
    limit: int = 200,
    history_sort_by: str = "recent",
    burndown_sort_by: str = "age",
    trend_days: int = 14,
    forecast_window_days: int = 7,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
) -> Dict[str, str]:
    return build_message_owner_rebalance_trend_row_urls(
        activity_date=activity_date,
        vendor_id=vendor_id,
        from_owner=from_owner,
        to_owner=to_owner,
        batch_id=batch_id,
        rollback_age_bucket=rollback_age_bucket,
        rollback_status=rollback_status,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        limit=limit,
        history_sort_by=history_sort_by,
        burndown_sort_by=burndown_sort_by,
        trend_days=trend_days,
        forecast_window_days=forecast_window_days,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
    )


def build_message_owner_rebalance_status_row_urls_bundle(
    *,
    rollback_status: str = "eligible",
    vendor_id: Optional[str] = None,
    from_owner: Optional[str] = None,
    to_owner: Optional[str] = None,
    batch_id: Optional[str] = None,
    rollback_age_bucket: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    strict_current_owner: bool = True,
    limit: int = 200,
    rollback_sort_by: str = "priority",
    burndown_sort_by: str = "age",
    trend_days: int = 14,
    forecast_window_days: int = 7,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
) -> Dict[str, str]:
    return build_message_owner_rebalance_status_row_urls(
        rollback_status=rollback_status,
        vendor_id=vendor_id,
        from_owner=from_owner,
        to_owner=to_owner,
        batch_id=batch_id,
        rollback_age_bucket=rollback_age_bucket,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        limit=limit,
        rollback_sort_by=rollback_sort_by,
        burndown_sort_by=burndown_sort_by,
        trend_days=trend_days,
        forecast_window_days=forecast_window_days,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
    )


def build_message_owner_rebalance_alert_summary_row_urls_bundle(
    *,
    alert_scope: str = "policy",
    vendor_id: Optional[str] = None,
    from_owner: Optional[str] = None,
    to_owner: Optional[str] = None,
    batch_id: Optional[str] = None,
    rollback_age_bucket: Optional[str] = None,
    rollback_status: Optional[str] = None,
    alert_level: Optional[str] = None,
    alert_execution_status: Optional[str] = None,
    alert_latest_outcome_status: Optional[str] = None,
    include_cross_vendor_only: bool = False,
    strict_current_owner: bool = True,
    limit: int = 200,
    burndown_sort_by: str = "age",
    trend_days: int = 14,
    forecast_window_days: int = 7,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
) -> Dict[str, str]:
    return build_message_owner_rebalance_alert_summary_row_urls(
        alert_scope=alert_scope,
        vendor_id=vendor_id,
        from_owner=from_owner,
        to_owner=to_owner,
        batch_id=batch_id,
        rollback_age_bucket=rollback_age_bucket,
        rollback_status=rollback_status,
        alert_level=alert_level,
        alert_execution_status=alert_execution_status,
        alert_latest_outcome_status=alert_latest_outcome_status,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        limit=limit,
        burndown_sort_by=burndown_sort_by,
        trend_days=trend_days,
        forecast_window_days=forecast_window_days,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
    )


def build_vendor_analytics_row_urls_bundle(
    *,
    vendor_id: str = "vendor-1",
) -> Dict[str, str]:
    return build_vendor_analytics_row_urls(vendor_id=vendor_id)


def build_receipt_analytics_row_urls_bundle(
    *,
    consumer_urls: Dict[str, str],
    vendor_id: Optional[str] = "vendor-1",
) -> Dict[str, str]:
    return build_receipt_analytics_row_urls(
        consumer_urls=consumer_urls,
        vendor_id=vendor_id,
    )
