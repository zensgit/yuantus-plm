"""Shared consumer row discoverability helpers for subcontracting router payloads."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlencode


def _query_path(path: str, params: Mapping[str, Any]) -> str:
    pairs: List[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            pairs.append((key, "true" if value else "false"))
            continue
        if isinstance(value, list):
            for item in value:
                if item is not None:
                    pairs.append((key, str(item)))
            continue
        pairs.append((key, str(value)))
    if not pairs:
        return path
    return f"{path}?{urlencode(pairs, doseq=True)}"


def _merge_message_ids(params: Optional[Mapping[str, Any]], message_id: Optional[str]) -> Dict[str, Any]:
    merged = dict(params or {})
    normalized_message_id = str(message_id or "").strip() or None
    existing_ids = [
        str(item).strip()
        for item in (merged.get("message_ids") or [])
        if str(item).strip()
    ]
    if normalized_message_id and normalized_message_id not in existing_ids:
        merged["message_ids"] = [*existing_ids, normalized_message_id]
    elif existing_ids:
        merged["message_ids"] = existing_ids
    return merged


def build_consumer_order_row_urls(
    *,
    consumer_urls: Mapping[str, str],
) -> Dict[str, str]:
    return dict(consumer_urls)


def build_return_disposition_approval_inbox_row_urls(
    *,
    consumer_urls: Mapping[str, str],
    order_id: str,
    disposition_event_id: Optional[str] = None,
) -> Dict[str, str]:
    return {
        **dict(consumer_urls),
        "approval_board": (
            f"/api/v1/subcontracting/orders/{order_id}/return-disposition-approval-board"
        ),
        "approval_assign": (
            f"/api/v1/subcontracting/orders/{order_id}/return-dispositions/{disposition_event_id}/assign"
            if disposition_event_id
            else None
        ),
    }


def build_vendor_message_board_row_urls(
    *,
    consumer_urls: Mapping[str, str],
    order_id: str,
) -> Dict[str, str]:
    return {
        **dict(consumer_urls),
        "thread": f"/api/v1/subcontracting/orders/{order_id}/vendor-messages",
    }


def build_message_owner_workload_message_row_urls(
    *,
    consumer_urls: Mapping[str, str],
    order_id: str,
    message_id: Optional[str] = None,
    workload_board_params: Optional[Mapping[str, Any]] = None,
    rebalance_preview_params: Optional[Mapping[str, Any]] = None,
    rebalance_history_params: Optional[Mapping[str, Any]] = None,
    rebalance_rollback_board_params: Optional[Mapping[str, Any]] = None,
) -> Dict[str, str]:
    urls = {
        **dict(consumer_urls),
        "thread": f"/api/v1/subcontracting/orders/{order_id}/vendor-messages",
    }
    if workload_board_params:
        urls["workload_board"] = _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            dict(workload_board_params),
        )
    if rebalance_preview_params:
        urls["rebalance_preview"] = _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview",
            _merge_message_ids(rebalance_preview_params, message_id),
        )
    if rebalance_history_params:
        urls["rebalance_history"] = _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            dict(rebalance_history_params),
        )
    if rebalance_rollback_board_params:
        urls["rebalance_rollback_board"] = _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board",
            dict(rebalance_rollback_board_params),
        )
    return urls


def build_vendor_portal_order_row_urls(
    *,
    consumer_urls: Mapping[str, str],
    vendor_id: str,
    include_closed: bool = False,
    timeline_limit: int = 3,
) -> Dict[str, str]:
    return {
        **dict(consumer_urls),
        "portal_board": _query_path(
            f"/api/v1/subcontracting/vendors/{vendor_id}/portal-board",
            {
                "include_closed": include_closed,
                "timeline_limit": timeline_limit,
            },
        ),
        "workspace": _query_path(
            f"/api/v1/subcontracting/vendors/{vendor_id}/workspace",
            {
                "include_closed": include_closed,
                "timeline_limit": timeline_limit,
            },
        ),
        "message_board": f"/api/v1/subcontracting/vendors/{vendor_id}/message-board",
        "message_sla_board": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/sla-board"
        ),
        "message_owner_inbox": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/owner-inbox"
        ),
        "message_owner_workload_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            {"vendor_id": vendor_id},
        ),
    }


def build_message_owner_workload_scope_params(
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
) -> Dict[str, Any]:
    return {
        "vendor_id": vendor_id,
        "owner": owner,
        "team": team,
        "include_closed": include_closed,
        "include_paused": include_paused,
        "message_limit": message_limit,
        "owner_soft_limit": owner_soft_limit,
        "owner_hard_limit": owner_hard_limit,
        "aged_watch_hours": aged_watch_hours,
        "aged_breach_hours": aged_breach_hours,
        "pause_watch_hours": pause_watch_hours,
        "pause_breach_hours": pause_breach_hours,
        "sort_by": sort_by,
    }


def build_message_owner_workload_owner_row_urls(
    *,
    owner: str,
    scope_params: Mapping[str, Any],
) -> Dict[str, str]:
    board_params = dict(scope_params)
    board_params["owner"] = owner
    history_params = {
        "vendor_id": scope_params.get("vendor_id"),
        "from_owner": owner,
    }
    return {
        "workload_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            board_params,
        ),
        "rebalance_preview": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview",
            board_params,
        ),
        "rebalance_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            history_params,
        ),
        "rebalance_rollback_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board",
            history_params,
        ),
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            history_params,
        ),
    }


def build_message_owner_workload_team_row_urls(
    *,
    team: str,
    scope_params: Mapping[str, Any],
) -> Dict[str, str]:
    board_params = dict(scope_params)
    board_params["team"] = team
    return {
        "workload_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            board_params,
        ),
        "rebalance_preview": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview",
            board_params,
        ),
    }


def build_message_owner_workload_vendor_row_urls(
    *,
    vendor_id: str,
    scope_params: Mapping[str, Any],
) -> Dict[str, str]:
    board_params = dict(scope_params)
    board_params["vendor_id"] = vendor_id
    history_params = {"vendor_id": vendor_id}
    return {
        "workload_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            board_params,
        ),
        "rebalance_preview": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview",
            board_params,
        ),
        "rebalance_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            history_params,
        ),
        "rebalance_rollback_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board",
            history_params,
        ),
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            history_params,
        ),
        "message_board": f"/api/v1/subcontracting/vendors/{vendor_id}/message-board",
        "message_sla_board": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/sla-board"
        ),
        "message_owner_inbox": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/owner-inbox"
        ),
        "portal_board": f"/api/v1/subcontracting/vendors/{vendor_id}/portal-board",
        "workspace": f"/api/v1/subcontracting/vendors/{vendor_id}/workspace",
        "execution_summary": (
            f"/api/v1/subcontracting/execution-summary?vendor_id={vendor_id}"
        ),
        "execution_summary_export": (
            f"/api/v1/subcontracting/execution-summary/export?format=json&vendor_id={vendor_id}"
        ),
    }


def build_message_owner_rebalance_batch_row_urls(
    *,
    batch_id: str,
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
    history_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
        "activity_outcome": activity_outcome,
        "selection_mode": selection_mode,
        "include_cross_vendor_only": include_cross_vendor_only,
        "limit": history_limit,
        "sort_by": history_sort_by,
    }
    rollback_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "rollback_age_bucket": rollback_age_bucket,
        "rollback_status": rollback_status,
        "include_cross_vendor_only": include_cross_vendor_only,
        "strict_current_owner": strict_current_owner,
        "limit": history_limit,
        "sort_by": rollback_sort_by,
    }
    return {
        "rebalance_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            history_params,
        ),
        "rebalance_rollback_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board",
            rollback_params,
        ),
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            rollback_params,
        ),
    }


def build_message_owner_rebalance_reason_row_urls(
    *,
    rebalance_reason: str,
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
    history_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
        "activity_outcome": activity_outcome,
        "selection_mode": selection_mode,
        "rebalance_reason": rebalance_reason,
        "include_cross_vendor_only": include_cross_vendor_only,
        "limit": limit,
        "sort_by": history_sort_by,
    }
    return {
        "rebalance_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            history_params,
        ),
        "rebalance_history_export": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history/export",
            {
                "format": "json",
                **history_params,
            },
        ),
    }


def build_message_owner_rebalance_latest_attempt_batch_urls(
    *,
    source_batch_id: str,
    attempt_batch_id: str,
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
    urls = build_message_owner_rebalance_batch_row_urls(
        batch_id=source_batch_id,
        vendor_id=vendor_id,
        from_owner=source_from_owner,
        to_owner=source_to_owner,
        rollback_age_bucket=rollback_age_bucket,
        rollback_status=rollback_status,
        include_cross_vendor_only=include_cross_vendor_only,
        strict_current_owner=strict_current_owner,
        history_limit=history_limit,
        history_sort_by=history_sort_by,
        rollback_sort_by=rollback_sort_by,
    )
    urls["rebalance_history"] = _query_path(
        "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
        {
            "vendor_id": vendor_id,
            "from_owner": attempt_from_owner,
            "to_owner": attempt_to_owner,
            "batch_id": attempt_batch_id,
            "activity_kind": "closed",
            "activity_outcome": attempt_activity_outcome,
            "selection_mode": "rollback",
            "include_cross_vendor_only": include_cross_vendor_only,
            "limit": history_limit,
            "sort_by": history_sort_by,
        },
    )
    return urls


def build_message_owner_rebalance_owner_row_urls(
    *,
    owner: str,
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
    workload_scope_params: Optional[Mapping[str, Any]] = None,
) -> Dict[str, str]:
    board_params = dict(
        workload_scope_params
        or build_message_owner_workload_scope_params(vendor_id=vendor_id)
    )
    board_params["owner"] = owner
    history_params = {
        "vendor_id": vendor_id,
        "from_owner": owner,
        "to_owner": to_owner,
        "batch_id": None,
        "rollback_status": rollback_status,
        "selection_mode": None,
        "include_cross_vendor_only": include_cross_vendor_only,
        "limit": history_limit,
        "sort_by": history_sort_by,
    }
    rollback_params = {
        "vendor_id": vendor_id,
        "from_owner": owner,
        "to_owner": to_owner,
        "batch_id": None,
        "rollback_age_bucket": rollback_age_bucket,
        "rollback_status": rollback_status,
        "include_cross_vendor_only": include_cross_vendor_only,
        "strict_current_owner": strict_current_owner,
        "limit": history_limit,
        "sort_by": rollback_sort_by,
    }
    burndown_params = {
        **rollback_params,
        "trend_days": 14,
        "forecast_window_days": 7,
        "sort_by": burndown_sort_by,
    }
    return {
        "workload_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            board_params,
        ),
        "rebalance_preview": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-preview",
            board_params,
        ),
        "rebalance_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            history_params,
        ),
        "rebalance_rollback_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board",
            rollback_params,
        ),
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            burndown_params,
        ),
    }


def build_message_owner_rebalance_age_row_urls(
    *,
    rollback_age_bucket: str,
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
    rollback_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "rollback_age_bucket": rollback_age_bucket,
        "rollback_status": rollback_status,
        "include_cross_vendor_only": include_cross_vendor_only,
        "strict_current_owner": strict_current_owner,
        "limit": limit,
        "sort_by": rollback_sort_by,
    }
    burndown_params = {
        **rollback_params,
        "sort_by": burndown_sort_by,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
    }
    return {
        "rebalance_rollback_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board",
            rollback_params,
        ),
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            burndown_params,
        ),
    }


def build_message_owner_rebalance_trend_row_urls(
    *,
    activity_date: str,
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
    history_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "activity_date": activity_date,
        "include_cross_vendor_only": include_cross_vendor_only,
        "limit": limit,
        "sort_by": history_sort_by,
    }
    burndown_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "rollback_age_bucket": rollback_age_bucket,
        "rollback_status": rollback_status,
        "include_cross_vendor_only": include_cross_vendor_only,
        "strict_current_owner": strict_current_owner,
        "limit": limit,
        "sort_by": burndown_sort_by,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
    }
    return {
        "rebalance_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            history_params,
        ),
        "opened_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            {
                **history_params,
                "activity_kind": "opened",
            },
        ),
        "closed_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            {
                **history_params,
                "activity_kind": "closed",
            },
        ),
        "rolled_back_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            {
                **history_params,
                "activity_kind": "closed",
                "activity_outcome": "applied",
            },
        ),
        "blocked_close_attempts_history": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-history",
            {
                **history_params,
                "activity_kind": "closed",
                "activity_outcome": "blocked_attempt",
            },
        ),
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            burndown_params,
        ),
    }


def build_message_owner_rebalance_status_row_urls(
    *,
    rollback_status: str,
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
    rollback_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "rollback_age_bucket": rollback_age_bucket,
        "rollback_status": rollback_status,
        "include_cross_vendor_only": include_cross_vendor_only,
        "strict_current_owner": strict_current_owner,
        "limit": limit,
        "sort_by": rollback_sort_by,
    }
    burndown_params = {
        **rollback_params,
        "sort_by": burndown_sort_by,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
    }
    return {
        "rebalance_rollback_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-board",
            rollback_params,
        ),
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            burndown_params,
        ),
    }


def build_message_owner_rebalance_alert_summary_row_urls(
    *,
    alert_scope: str,
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
    burndown_params = {
        "vendor_id": vendor_id,
        "from_owner": from_owner,
        "to_owner": to_owner,
        "batch_id": batch_id,
        "rollback_age_bucket": rollback_age_bucket,
        "rollback_status": rollback_status,
        "alert_scope": alert_scope,
        "alert_level": alert_level,
        "alert_execution_status": alert_execution_status,
        "alert_latest_outcome_status": alert_latest_outcome_status,
        "include_cross_vendor_only": include_cross_vendor_only,
        "strict_current_owner": strict_current_owner,
        "limit": limit,
        "sort_by": burndown_sort_by,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
    }
    return {
        "rebalance_rollback_burndown": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown",
            burndown_params,
        ),
        "rebalance_rollback_burndown_export": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board/rebalance-rollback-burndown/export",
            {
                "format": "json",
                **burndown_params,
            },
        ),
    }


def build_vendor_analytics_row_urls(
    *,
    vendor_id: str,
) -> Dict[str, str]:
    return {
        "portal_board": f"/api/v1/subcontracting/vendors/{vendor_id}/portal-board",
        "workspace": f"/api/v1/subcontracting/vendors/{vendor_id}/workspace",
        "message_board": f"/api/v1/subcontracting/vendors/{vendor_id}/message-board",
        "message_sla_board": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/sla-board"
        ),
        "message_owner_inbox": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/owner-inbox"
        ),
        "message_owner_workload_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            {"vendor_id": vendor_id},
        ),
        "execution_summary": (
            f"/api/v1/subcontracting/execution-summary?vendor_id={vendor_id}"
        ),
        "execution_summary_export": (
            f"/api/v1/subcontracting/execution-summary/export?format=json&vendor_id={vendor_id}"
        ),
    }


def build_receipt_analytics_row_urls(
    *,
    consumer_urls: Mapping[str, str],
    vendor_id: Optional[str] = None,
) -> Dict[str, str]:
    if not vendor_id:
        return dict(consumer_urls)
    return {
        **dict(consumer_urls),
        "portal_board": f"/api/v1/subcontracting/vendors/{vendor_id}/portal-board",
        "workspace": f"/api/v1/subcontracting/vendors/{vendor_id}/workspace",
        "message_board": f"/api/v1/subcontracting/vendors/{vendor_id}/message-board",
        "message_sla_board": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/sla-board"
        ),
        "message_owner_inbox": (
            f"/api/v1/subcontracting/vendors/{vendor_id}/message-board/owner-inbox"
        ),
        "message_owner_workload_board": _query_path(
            "/api/v1/subcontracting/message-owner-workload-board",
            {"vendor_id": vendor_id},
        ),
        "vendor_analytics": "/api/v1/subcontracting/vendors/analytics",
    }
