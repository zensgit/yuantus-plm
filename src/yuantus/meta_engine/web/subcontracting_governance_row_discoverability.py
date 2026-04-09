"""Scoped governance row discoverability helpers for subcontracting router payloads."""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlencode

from yuantus.meta_engine.web.subcontracting_governance_discoverability import (
    governance_discoverability_path,
)


def build_governance_scoped_path(
    code: str,
    params: Optional[Mapping[str, Any]] = None,
) -> str:
    return build_governance_scoped_path_from_path(
        governance_discoverability_path(code),
        params,
    )


def build_governance_scoped_path_from_path(
    path: str,
    params: Optional[Mapping[str, Any]] = None,
) -> str:
    pairs = []
    for key, value in (params or {}).items():
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


def build_governance_scoped_export_path(
    code: str,
    params: Optional[Mapping[str, Any]] = None,
) -> str:
    return build_governance_scoped_path_from_path(
        f"{governance_discoverability_path(code)}/export",
        {"format": "json", **dict(params or {})},
    )


def build_governance_window_query(
    base_query: Mapping[str, Any],
    *,
    review_limit: Optional[int] = None,
    handoff_limit: Optional[int] = None,
    history_limit: Optional[int] = None,
    sort_by: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        **dict(base_query),
        **({"review_limit": review_limit} if review_limit is not None else {}),
        **({"handoff_limit": handoff_limit} if handoff_limit is not None else {}),
        **({"history_limit": history_limit} if history_limit is not None else {}),
        **({"sort_by": sort_by} if sort_by is not None else {}),
    }


def _governance_action_history_query(
    *,
    vendor_id: Optional[str] = None,
    queue_type: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    team: Optional[str] = None,
    batch_id: Optional[str] = None,
    source_ref: Optional[str] = None,
    open_only: bool = False,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    sort_by: str = "recent",
) -> Dict[str, Any]:
    return {
        "vendor_id": vendor_id,
        "queue_type": queue_type,
        "action": action,
        "actor": actor,
        "team": team,
        "batch_id": batch_id,
        "source_ref": source_ref,
        "open_only": open_only,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
        "limit": limit,
        "sort_by": sort_by,
    }


def _governance_action_burndown_query(
    *,
    vendor_id: Optional[str] = None,
    queue_type: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    team: Optional[str] = None,
    batch_id: Optional[str] = None,
    source_ref: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    sort_by: str = "recent",
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, Any]:
    return {
        "vendor_id": vendor_id,
        "queue_type": queue_type,
        "action": action,
        "actor": actor,
        "team": team,
        "batch_id": batch_id,
        "source_ref": source_ref,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
        "limit": limit,
        "sort_by": sort_by,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }


def _governance_action_analytics_urls(
    *,
    history_query: Mapping[str, Any],
    burndown_query: Mapping[str, Any],
) -> Dict[str, str]:
    return {
        "governance_history": build_governance_scoped_path(
            "governance_history",
            history_query,
        ),
        "governance_history_export": build_governance_scoped_export_path(
            "governance_history",
            history_query,
        ),
        "governance_burndown": build_governance_scoped_path(
            "governance_burndown",
            burndown_query,
        ),
        "governance_burndown_export": build_governance_scoped_export_path(
            "governance_burndown",
            burndown_query,
        ),
    }


def build_governance_review_digest_history_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    queue_type: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    history_sort_by: str = "recent",
    burndown_sort_by: str = "recent",
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    history_query = _governance_action_history_query(
        vendor_id=vendor_id,
        queue_type=queue_type,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
        limit=limit,
        sort_by=history_sort_by,
    )
    burndown_query = _governance_action_burndown_query(
        vendor_id=vendor_id,
        queue_type=queue_type,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
        limit=limit,
        sort_by=burndown_sort_by,
        trend_days=trend_days,
        forecast_window_days=forecast_window_days,
    )
    history_path = build_governance_scoped_path("governance_history", history_query)
    history_export = build_governance_scoped_export_path(
        "governance_history",
        history_query,
    )
    burndown_path = build_governance_scoped_path(
        "governance_burndown",
        burndown_query,
    )
    burndown_export = build_governance_scoped_export_path(
        "governance_burndown",
        burndown_query,
    )
    return {
        "self": history_path,
        "export": history_export,
        "burndown": burndown_path,
        "burndown_export": burndown_export,
        "primary_target": history_path,
    }


def build_governance_review_digest_burndown_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    queue_type: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    history_sort_by: str = "recent",
    burndown_sort_by: str = "recent",
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    history_query = _governance_action_history_query(
        vendor_id=vendor_id,
        queue_type=queue_type,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
        limit=limit,
        sort_by=history_sort_by,
    )
    burndown_query = _governance_action_burndown_query(
        vendor_id=vendor_id,
        queue_type=queue_type,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
        limit=limit,
        sort_by=burndown_sort_by,
        trend_days=trend_days,
        forecast_window_days=forecast_window_days,
    )
    history_path = build_governance_scoped_path("governance_history", history_query)
    history_export = build_governance_scoped_export_path(
        "governance_history",
        history_query,
    )
    burndown_path = build_governance_scoped_path(
        "governance_burndown",
        burndown_query,
    )
    burndown_export = build_governance_scoped_export_path(
        "governance_burndown",
        burndown_query,
    )
    return {
        "self": burndown_path,
        "export": burndown_export,
        "history": history_path,
        "history_export": history_export,
        "primary_target": burndown_path,
    }


def build_governance_review_handoff_ledger_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "priority",
) -> Dict[str, str]:
    ledger_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "preset_code": preset_code,
            "preview_limit": preview_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        review_limit=review_limit,
        handoff_limit=handoff_limit,
    )
    review_digest_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }
    history_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "preview_limit": preview_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        review_limit=review_limit,
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    acceptance_digest_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "preview_limit": preview_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        review_limit=review_limit,
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    acceptance_trends_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "preview_limit": preview_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        review_limit=review_limit,
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    follow_through_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "open_only": open_only,
            "preview_limit": preview_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        review_limit=review_limit,
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )

    ledger_path = build_governance_scoped_path(
        "governance_review_handoff",
        ledger_query,
    )
    ledger_export = build_governance_scoped_export_path(
        "governance_review_handoff",
        ledger_query,
    )
    review_digest_path = build_governance_scoped_path(
        "governance_review_digest",
        review_digest_query,
    )
    review_digest_export = build_governance_scoped_export_path(
        "governance_review_digest",
        review_digest_query,
    )
    history_path = build_governance_scoped_path(
        "governance_review_handoff_history",
        history_query,
    )
    history_export = build_governance_scoped_export_path(
        "governance_review_handoff_history",
        history_query,
    )
    acceptance_digest_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_digest",
        acceptance_digest_query,
    )
    acceptance_digest_export = build_governance_scoped_export_path(
        "governance_review_handoff_acceptance_digest",
        acceptance_digest_query,
    )
    acceptance_trends_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_trends",
        acceptance_trends_query,
    )
    acceptance_trends_export = build_governance_scoped_export_path(
        "governance_review_handoff_acceptance_trends",
        acceptance_trends_query,
    )
    follow_through_digest_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_follow_through_digest",
        follow_through_query,
    )
    follow_through_digest_export = build_governance_scoped_export_path(
        "governance_review_handoff_acceptance_follow_through_digest",
        follow_through_query,
    )
    follow_through_history_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_follow_through_history",
        follow_through_query,
    )
    follow_through_history_export = build_governance_scoped_export_path(
        "governance_review_handoff_acceptance_follow_through_history",
        follow_through_query,
    )
    follow_through_burndown_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_follow_through_burndown",
        follow_through_query,
    )
    follow_through_burndown_export = build_governance_scoped_export_path(
        "governance_review_handoff_acceptance_follow_through_burndown",
        follow_through_query,
    )
    return {
        "self": ledger_path,
        "export": ledger_export,
        "review_handoff": ledger_path,
        "review_handoff_export": ledger_export,
        "review_digest": review_digest_path,
        "review_digest_export": review_digest_export,
        "review_handoff_history": history_path,
        "review_handoff_history_export": history_export,
        "acceptance_digest": acceptance_digest_path,
        "acceptance_digest_export": acceptance_digest_export,
        "acceptance_trends": acceptance_trends_path,
        "acceptance_trends_export": acceptance_trends_export,
        "follow_through_digest": follow_through_digest_path,
        "follow_through_digest_export": follow_through_digest_export,
        "follow_through_history": follow_through_history_path,
        "follow_through_history_export": follow_through_history_export,
        "follow_through_burndown": follow_through_burndown_path,
        "follow_through_burndown_export": follow_through_burndown_export,
        "primary_target": ledger_path,
    }


def build_governance_review_handoff_acceptance_digest_history_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "priority",
) -> Dict[str, str]:
    history_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "open_only": open_only,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    digest_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "open_only": open_only,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    trends_query = dict(digest_query)
    history_path = build_governance_scoped_path(
        "governance_review_handoff_history",
        history_query,
    )
    return {
        "self": history_path,
        "export": build_governance_scoped_export_path(
            "governance_review_handoff_history",
            history_query,
        ),
        "acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            digest_query,
        ),
        "acceptance_digest_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_digest",
            digest_query,
        ),
        "acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "acceptance_trends_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "primary_target": history_path,
    }


def build_governance_review_handoff_follow_through_digest_history_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "priority",
) -> Dict[str, str]:
    scope_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_mode": selection_mode,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }
    digest_query = build_governance_window_query(
        scope_query,
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    history_query = build_governance_window_query(
        {
            **scope_query,
            "selection_view_id": selection_view_id,
            "follow_through_status": follow_through_status,
            "follow_through_state": follow_through_state,
            "open_only": open_only,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    burndown_query = build_governance_window_query(
        {
            **scope_query,
            "follow_through_state": follow_through_state,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    history_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_follow_through_history",
        history_query,
    )
    return {
        "self": history_path,
        "export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_history",
            history_query,
        ),
        "follow_through_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            digest_query,
        ),
        "follow_through_digest_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            digest_query,
        ),
        "follow_through_burndown": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            burndown_query,
        ),
        "follow_through_burndown_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            burndown_query,
        ),
        "primary_target": history_path,
    }


def build_governance_review_handoff_follow_through_digest_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "priority",
) -> Dict[str, str]:
    trends_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    acceptance_digest_query = {
        **trends_query,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "acceptance_action": acceptance_action,
    }
    follow_through_query = {
        **acceptance_digest_query,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "acceptance_action": acceptance_action,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
    }
    entry_efficiency_query = dict(follow_through_query)
    review_digest_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }
    digest_query = build_governance_window_query(
        follow_through_query,
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    history_query = build_governance_window_query(
        {
            **follow_through_query,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    burndown_query = build_governance_window_query(
        {
            **follow_through_query,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    digest_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_follow_through_digest",
        digest_query,
    )
    return {
        "self": digest_path,
        "export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            digest_query,
        ),
        "acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            acceptance_digest_query,
        ),
        "acceptance_digest_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_digest",
            acceptance_digest_query,
        ),
        "acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "acceptance_trends_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "follow_through_history": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_history",
            history_query,
        ),
        "follow_through_history_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_history",
            history_query,
        ),
        "follow_through_burndown": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            burndown_query,
        ),
        "follow_through_burndown_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            burndown_query,
        ),
        "entry_efficiency": build_governance_scoped_path(
            "governance_review_handoff_acceptance_entry_efficiency",
            entry_efficiency_query,
        ),
        "entry_efficiency_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_entry_efficiency",
            entry_efficiency_query,
        ),
        "review_digest": build_governance_scoped_path(
            "governance_review_digest",
            review_digest_query,
        ),
        "review_digest_export": build_governance_scoped_export_path(
            "governance_review_digest",
            review_digest_query,
        ),
        "primary_target": digest_path,
    }


def build_governance_review_handoff_follow_through_burndown_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "priority",
) -> Dict[str, str]:
    digest_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "follow_through_state": follow_through_state,
            "open_only": open_only,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    history_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "follow_through_state": follow_through_state,
            "open_only": open_only,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    burndown_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "follow_through_state": follow_through_state,
            "open_only": open_only,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    burndown_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_follow_through_burndown",
        burndown_query,
    )
    return {
        "self": burndown_path,
        "export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            burndown_query,
        ),
        "follow_through_history": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_history",
            history_query,
        ),
        "follow_through_history_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_history",
            history_query,
        ),
        "follow_through_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            digest_query,
        ),
        "follow_through_digest_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            digest_query,
        ),
        "primary_target": burndown_path,
    }


def build_governance_review_handoff_acceptance_trends_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "priority",
) -> Dict[str, str]:
    trends_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "open_only": open_only,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    digest_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "open_only": open_only,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    history_query = build_governance_window_query(
        {
            "vendor_id": vendor_id,
            "responsible_actor": responsible_actor,
            "responsible_team": responsible_team,
            "on_call_owner": on_call_owner,
            "on_call_team": on_call_team,
            "current_handoff_owner": current_handoff_owner,
            "current_handoff_team": current_handoff_team,
            "preset_code": preset_code,
            "accepted_by": accepted_by,
            "action_batch_id": action_batch_id,
            "acceptance_action": acceptance_action,
            "acceptance_status": acceptance_status,
            "selection_view_id": selection_view_id,
            "selection_mode": selection_mode,
            "follow_through_status": follow_through_status,
            "action_origin": action_origin,
            "queue_type": queue_type,
            "open_only": open_only,
            "activity_date": activity_date,
            "activity_kind": activity_kind,
            "preview_limit": preview_limit,
            "review_limit": review_limit,
            "trend_days": trend_days,
            "forecast_window_days": forecast_window_days,
        },
        handoff_limit=handoff_limit,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    trends_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_trends",
        trends_query,
    )
    return {
        "self": trends_path,
        "export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            digest_query,
        ),
        "acceptance_digest_export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_digest",
            digest_query,
        ),
        "history": build_governance_scoped_path(
            "governance_review_handoff_history",
            history_query,
        ),
        "history_export": build_governance_scoped_export_path(
            "governance_review_handoff_history",
            history_query,
        ),
        "primary_target": trends_path,
    }


def build_governance_action_actor_row_urls(
    *,
    actor: str,
    vendor_id: Optional[str] = None,
    queue_type: Optional[str] = None,
    action: Optional[str] = None,
    team: Optional[str] = None,
    batch_id: Optional[str] = None,
    source_ref: Optional[str] = None,
    open_only: bool = False,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    history_sort_by: str = "recent",
    burndown_sort_by: str = "recent",
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    return _governance_action_analytics_urls(
        history_query=_governance_action_history_query(
            vendor_id=vendor_id,
            queue_type=queue_type,
            action=action,
            actor=actor,
            team=team,
            batch_id=batch_id,
            source_ref=source_ref,
            open_only=open_only,
            on_call_owner=on_call_owner,
            on_call_team=on_call_team,
            include_watch_alerts=include_watch_alerts,
            limit=limit,
            sort_by=history_sort_by,
        ),
        burndown_query=_governance_action_burndown_query(
            vendor_id=vendor_id,
            queue_type=queue_type,
            action=action,
            actor=actor,
            team=team,
            batch_id=batch_id,
            source_ref=source_ref,
            on_call_owner=on_call_owner,
            on_call_team=on_call_team,
            include_watch_alerts=include_watch_alerts,
            limit=limit,
            sort_by=burndown_sort_by,
            trend_days=trend_days,
            forecast_window_days=forecast_window_days,
        ),
    )


def build_governance_action_batch_row_urls(
    *,
    batch_id: str,
    vendor_id: Optional[str] = None,
    queue_type: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    team: Optional[str] = None,
    source_ref: Optional[str] = None,
    open_only: bool = False,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    history_sort_by: str = "recent",
    burndown_sort_by: str = "recent",
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    return _governance_action_analytics_urls(
        history_query=_governance_action_history_query(
            vendor_id=vendor_id,
            queue_type=queue_type,
            action=action,
            actor=actor,
            team=team,
            batch_id=batch_id,
            source_ref=source_ref,
            open_only=open_only,
            on_call_owner=on_call_owner,
            on_call_team=on_call_team,
            include_watch_alerts=include_watch_alerts,
            limit=limit,
            sort_by=history_sort_by,
        ),
        burndown_query=_governance_action_burndown_query(
            vendor_id=vendor_id,
            queue_type=queue_type,
            action=action,
            actor=actor,
            team=team,
            batch_id=batch_id,
            source_ref=source_ref,
            on_call_owner=on_call_owner,
            on_call_team=on_call_team,
            include_watch_alerts=include_watch_alerts,
            limit=limit,
            sort_by=burndown_sort_by,
            trend_days=trend_days,
            forecast_window_days=forecast_window_days,
        ),
    )


def build_governance_action_row_urls(
    *,
    action: str,
    vendor_id: Optional[str] = None,
    queue_type: Optional[str] = None,
    actor: Optional[str] = None,
    team: Optional[str] = None,
    batch_id: Optional[str] = None,
    source_ref: Optional[str] = None,
    open_only: bool = False,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    history_sort_by: str = "recent",
    burndown_sort_by: str = "recent",
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    return _governance_action_analytics_urls(
        history_query=_governance_action_history_query(
            vendor_id=vendor_id,
            queue_type=queue_type,
            action=action,
            actor=actor,
            team=team,
            batch_id=batch_id,
            source_ref=source_ref,
            open_only=open_only,
            on_call_owner=on_call_owner,
            on_call_team=on_call_team,
            include_watch_alerts=include_watch_alerts,
            limit=limit,
            sort_by=history_sort_by,
        ),
        burndown_query=_governance_action_burndown_query(
            vendor_id=vendor_id,
            queue_type=queue_type,
            action=action,
            actor=actor,
            team=team,
            batch_id=batch_id,
            source_ref=source_ref,
            on_call_owner=on_call_owner,
            on_call_team=on_call_team,
            include_watch_alerts=include_watch_alerts,
            limit=limit,
            sort_by=burndown_sort_by,
            trend_days=trend_days,
            forecast_window_days=forecast_window_days,
        ),
    )


def build_governance_action_queue_summary_row_urls(
    *,
    queue_type: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    include_completed: bool = False,
    include_controlled: bool = True,
    actionable_only: bool = False,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    team: Optional[str] = None,
    batch_id: Optional[str] = None,
    source_ref: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    history_sort_by: str = "recent",
    burndown_sort_by: str = "recent",
    approval_gap_watch_hours: int = 24,
    approval_gap_breach_hours: int = 72,
    cleanup_watch_hours: int = 24,
    cleanup_breach_hours: int = 72,
    rollback_watch_hours: int = 24,
    rollback_breach_hours: int = 72,
    action_watch_hours: int = 24,
    action_stale_hours: int = 72,
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    history_query = _governance_action_history_query(
        vendor_id=vendor_id,
        queue_type=queue_type,
        action=action,
        actor=actor,
        team=team,
        batch_id=batch_id,
        source_ref=source_ref,
        open_only=False,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
        limit=limit,
        sort_by=history_sort_by,
    )
    burndown_query = _governance_action_burndown_query(
        vendor_id=vendor_id,
        queue_type=queue_type,
        action=action,
        actor=actor,
        team=team,
        batch_id=batch_id,
        source_ref=source_ref,
        on_call_owner=on_call_owner,
        on_call_team=on_call_team,
        include_watch_alerts=include_watch_alerts,
        limit=limit,
        sort_by=burndown_sort_by,
        trend_days=trend_days,
        forecast_window_days=forecast_window_days,
    )
    inbox_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "queue_type": queue_type,
        "include_completed": include_completed,
        "include_controlled": include_controlled,
        "actionable_only": actionable_only,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
        "limit": limit,
        "sort_by": "priority",
    }
    analytics_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "queue_type": queue_type,
        "include_completed": include_completed,
        "include_controlled": include_controlled,
        "actionable_only": actionable_only,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
        "limit": limit,
        "sort_by": "priority",
    }
    return {
        "governance_inbox": build_governance_scoped_path(
            "governance_inbox",
            inbox_query,
        ),
        "governance_inbox_export": build_governance_scoped_export_path(
            "governance_inbox",
            inbox_query,
        ),
        "governance_correlation": build_governance_scoped_path(
            "governance_correlation",
            analytics_query,
        ),
        "governance_correlation_export": build_governance_scoped_export_path(
            "governance_correlation",
            analytics_query,
        ),
        "governance_sla_board": build_governance_scoped_path(
            "governance_sla_board",
            analytics_query,
        ),
        "governance_sla_board_export": build_governance_scoped_export_path(
            "governance_sla_board",
            analytics_query,
        ),
        **_governance_action_analytics_urls(
            history_query=history_query,
            burndown_query=burndown_query,
        ),
    }


def build_governance_responsibility_actor_summary_row_urls(
    *,
    responsible_actor: str,
    vendor_id: Optional[str] = None,
    responsible_team: Optional[str] = None,
    queue_type: Optional[str] = None,
    include_completed: bool = False,
    include_controlled: bool = True,
    actionable_only: bool = False,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    inbox_sort_by: str = "priority",
    correlation_sort_by: str = "priority",
    approval_gap_watch_hours: int = 24,
    approval_gap_breach_hours: int = 72,
    cleanup_watch_hours: int = 24,
    cleanup_breach_hours: int = 72,
    rollback_watch_hours: int = 24,
    rollback_breach_hours: int = 72,
    action_watch_hours: int = 24,
    action_stale_hours: int = 72,
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    inbox_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "queue_type": queue_type,
        "include_completed": include_completed,
        "include_controlled": include_controlled,
        "actionable_only": actionable_only,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
        "limit": limit,
        "sort_by": inbox_sort_by,
    }
    correlation_query = {
        **inbox_query,
        "sort_by": correlation_sort_by,
        "approval_gap_watch_hours": approval_gap_watch_hours,
        "approval_gap_breach_hours": approval_gap_breach_hours,
        "cleanup_watch_hours": cleanup_watch_hours,
        "cleanup_breach_hours": cleanup_breach_hours,
        "rollback_watch_hours": rollback_watch_hours,
        "rollback_breach_hours": rollback_breach_hours,
        "action_watch_hours": action_watch_hours,
        "action_stale_hours": action_stale_hours,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }
    sla_query = {
        **inbox_query,
        "sort_by": correlation_sort_by,
        "approval_gap_watch_hours": approval_gap_watch_hours,
        "approval_gap_breach_hours": approval_gap_breach_hours,
        "cleanup_watch_hours": cleanup_watch_hours,
        "cleanup_breach_hours": cleanup_breach_hours,
        "rollback_watch_hours": rollback_watch_hours,
        "rollback_breach_hours": rollback_breach_hours,
    }
    return {
        "governance_inbox": build_governance_scoped_path(
            "governance_inbox",
            inbox_query,
        ),
        "governance_inbox_export": build_governance_scoped_export_path(
            "governance_inbox",
            inbox_query,
        ),
        "governance_correlation": build_governance_scoped_path(
            "governance_correlation",
            correlation_query,
        ),
        "governance_correlation_export": build_governance_scoped_export_path(
            "governance_correlation",
            correlation_query,
        ),
        "governance_sla_board": build_governance_scoped_path(
            "governance_sla_board",
            sla_query,
        ),
        "governance_sla_board_export": build_governance_scoped_export_path(
            "governance_sla_board",
            sla_query,
        ),
    }


def build_governance_responsibility_team_summary_row_urls(
    *,
    responsible_team: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    queue_type: Optional[str] = None,
    include_completed: bool = False,
    include_controlled: bool = True,
    actionable_only: bool = False,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    include_watch_alerts: bool = True,
    limit: int = 200,
    inbox_sort_by: str = "priority",
    correlation_sort_by: str = "priority",
    approval_gap_watch_hours: int = 24,
    approval_gap_breach_hours: int = 72,
    cleanup_watch_hours: int = 24,
    cleanup_breach_hours: int = 72,
    rollback_watch_hours: int = 24,
    rollback_breach_hours: int = 72,
    action_watch_hours: int = 24,
    action_stale_hours: int = 72,
    trend_days: int = 14,
    forecast_window_days: int = 7,
) -> Dict[str, str]:
    inbox_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "queue_type": queue_type,
        "include_completed": include_completed,
        "include_controlled": include_controlled,
        "actionable_only": actionable_only,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "include_watch_alerts": include_watch_alerts,
        "limit": limit,
        "sort_by": inbox_sort_by,
    }
    correlation_query = {
        **inbox_query,
        "sort_by": correlation_sort_by,
        "approval_gap_watch_hours": approval_gap_watch_hours,
        "approval_gap_breach_hours": approval_gap_breach_hours,
        "cleanup_watch_hours": cleanup_watch_hours,
        "cleanup_breach_hours": cleanup_breach_hours,
        "rollback_watch_hours": rollback_watch_hours,
        "rollback_breach_hours": rollback_breach_hours,
        "action_watch_hours": action_watch_hours,
        "action_stale_hours": action_stale_hours,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }
    sla_query = {
        **inbox_query,
        "sort_by": correlation_sort_by,
        "approval_gap_watch_hours": approval_gap_watch_hours,
        "approval_gap_breach_hours": approval_gap_breach_hours,
        "cleanup_watch_hours": cleanup_watch_hours,
        "cleanup_breach_hours": cleanup_breach_hours,
        "rollback_watch_hours": rollback_watch_hours,
        "rollback_breach_hours": rollback_breach_hours,
    }
    return {
        "governance_inbox": build_governance_scoped_path(
            "governance_inbox",
            inbox_query,
        ),
        "governance_inbox_export": build_governance_scoped_export_path(
            "governance_inbox",
            inbox_query,
        ),
        "governance_correlation": build_governance_scoped_path(
            "governance_correlation",
            correlation_query,
        ),
        "governance_correlation_export": build_governance_scoped_export_path(
            "governance_correlation",
            correlation_query,
        ),
        "governance_sla_board": build_governance_scoped_path(
            "governance_sla_board",
            sla_query,
        ),
        "governance_sla_board_export": build_governance_scoped_export_path(
            "governance_sla_board",
            sla_query,
        ),
    }


def build_governance_review_handoff_acceptance_entry_efficiency_row_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    return {
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_entry_efficiency_snapshot_urls(
    *,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    snapshot_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    trends_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    acceptance_digest_query = {
        **trends_query,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
    }
    follow_through_query = {
        **acceptance_digest_query,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
    }
    review_digest_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }
    self_path = build_governance_scoped_path(
        "governance_review_handoff_acceptance_entry_efficiency",
        snapshot_query,
    )
    return {
        "self": self_path,
        "export": build_governance_scoped_export_path(
            "governance_review_handoff_acceptance_entry_efficiency",
            snapshot_query,
        ),
        "governance_review_handoff_acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            acceptance_digest_query,
        ),
        "governance_review_handoff_acceptance_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_digest",
                acceptance_digest_query,
            )
        ),
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "governance_review_handoff_acceptance_trends_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                trends_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_digest": build_governance_scoped_path(
            "governance_review_digest",
            review_digest_query,
        ),
        "governance_review_digest_export": build_governance_scoped_export_path(
            "governance_review_digest",
            review_digest_query,
        ),
        "primary_target": self_path,
    }


def build_governance_review_handoff_acceptance_selection_mode_row_urls(
    *,
    selection_mode: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    follow_through_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    entry_efficiency_query = {
        **follow_through_query,
        "activity_date": None,
        "activity_kind": None,
    }
    return {
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_action_row_urls(
    *,
    acceptance_action: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    trends_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    acceptance_digest_query = {
        **trends_query,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
    }
    follow_through_query = {
        **acceptance_digest_query,
        "acceptance_status": None,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
    }
    entry_efficiency_query = {
        **acceptance_digest_query,
        "acceptance_status": None,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
    }
    return {
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "governance_review_handoff_acceptance_trends_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                trends_query,
            )
        ),
        "governance_review_handoff_acceptance_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_digest",
                acceptance_digest_query,
            )
        ),
        "governance_review_handoff_acceptance_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_digest",
                acceptance_digest_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_status_row_urls(
    *,
    acceptance_status: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    trends_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
    }
    digest_query = {
        **trends_query,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": None,
        "activity_kind": None,
    }
    return {
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "governance_review_handoff_acceptance_trends_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                trends_query,
            )
        ),
        "governance_review_handoff_acceptance_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_digest",
                digest_query,
            )
        ),
        "governance_review_handoff_acceptance_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_digest",
                digest_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_follow_through_status_row_urls(
    *,
    follow_through_status: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    follow_through_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    entry_efficiency_query = {
        **follow_through_query,
        "activity_date": None,
        "activity_kind": None,
    }
    return {
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_follow_through_state_row_urls(
    *,
    follow_through_state: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    follow_through_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    entry_efficiency_query = {
        **follow_through_query,
        "activity_date": None,
        "activity_kind": None,
    }
    return {
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_queue_row_urls(
    *,
    queue_type: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    follow_through_state: Optional[str] = None,
    action_origin: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    trends_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "queue_type": queue_type,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    acceptance_digest_query = {
        **trends_query,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
    }
    follow_through_query = {
        **acceptance_digest_query,
        "acceptance_status": None,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "acceptance_action": acceptance_action,
        "action_origin": action_origin,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
    }
    entry_efficiency_query = {
        **acceptance_digest_query,
        "acceptance_status": None,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "follow_through_state": follow_through_state,
        "acceptance_action": acceptance_action,
        "action_origin": action_origin,
        "open_only": open_only,
    }
    return {
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "governance_review_handoff_acceptance_trends_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                trends_query,
            )
        ),
        "governance_review_handoff_acceptance_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_digest",
                acceptance_digest_query,
            )
        ),
        "governance_review_handoff_acceptance_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_digest",
                acceptance_digest_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_actor_row_urls(
    *,
    accepted_by: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    trends_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    acceptance_digest_query = {
        **trends_query,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
    }
    follow_through_query = {
        **acceptance_digest_query,
        "acceptance_status": None,
        "action_batch_id": action_batch_id,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "acceptance_action": acceptance_action,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
    }
    entry_efficiency_query = {
        **follow_through_query,
        "action_origin": action_origin,
        "queue_type": queue_type,
    }
    return {
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            trends_query,
        ),
        "governance_review_handoff_acceptance_trends_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                trends_query,
            )
        ),
        "governance_review_handoff_acceptance_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_digest",
                acceptance_digest_query,
            )
        ),
        "governance_review_handoff_acceptance_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_digest",
                acceptance_digest_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_follow_through_owner_row_urls(
    *,
    current_handoff_owner: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    digest_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    follow_through_query = {
        **digest_query,
        "action_batch_id": action_batch_id,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "acceptance_action": acceptance_action,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
    }
    entry_efficiency_query = {
        **digest_query,
        "action_batch_id": action_batch_id,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "acceptance_action": acceptance_action,
        "open_only": open_only,
    }
    return {
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_follow_through_view_row_urls(
    *,
    selection_view_id: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    digest_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    follow_through_query = {
        **digest_query,
        "action_batch_id": action_batch_id,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "acceptance_action": acceptance_action,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
    }
    entry_efficiency_query = {
        **digest_query,
        "action_batch_id": action_batch_id,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "acceptance_action": acceptance_action,
        "open_only": open_only,
    }
    return {
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                digest_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                digest_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_trend_row_urls(
    *,
    activity_date: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": activity_date,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    return {
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            query,
        ),
        "governance_review_handoff_acceptance_trends_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                query,
            )
        ),
        "governance_review_handoff_acceptance_trends_opened": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_trends",
                {
                    **query,
                    "activity_kind": "opened",
                },
            )
        ),
        "governance_review_handoff_acceptance_trends_opened_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                {
                    **query,
                    "activity_kind": "opened",
                },
            )
        ),
        "governance_review_handoff_acceptance_trends_accepted": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_trends",
                {
                    **query,
                    "activity_kind": "accepted",
                },
            )
        ),
        "governance_review_handoff_acceptance_trends_accepted_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_trends",
                {
                    **query,
                    "activity_kind": "accepted",
                },
            )
        ),
    }


def build_governance_review_handoff_acceptance_follow_through_batch_row_urls(
    *,
    action_batch_id: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    activity_date: Optional[str] = None,
    activity_kind: Optional[str] = None,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    digest_query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    follow_through_query = {
        **digest_query,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "acceptance_action": acceptance_action,
        "open_only": open_only,
        "activity_date": activity_date,
        "activity_kind": activity_kind,
    }
    entry_efficiency_query = {
        **digest_query,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "acceptance_action": acceptance_action,
        "open_only": open_only,
    }
    return {
        "governance_review_handoff_acceptance_follow_through_digest": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                digest_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_history_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_history",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_digest_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_digest",
                digest_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                follow_through_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
        "governance_review_handoff_acceptance_entry_efficiency_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_entry_efficiency",
                entry_efficiency_query,
            )
        ),
    }


def build_governance_review_handoff_acceptance_follow_through_trend_row_urls(
    *,
    activity_date: str,
    vendor_id: Optional[str] = None,
    responsible_actor: Optional[str] = None,
    responsible_team: Optional[str] = None,
    on_call_owner: Optional[str] = None,
    on_call_team: Optional[str] = None,
    current_handoff_owner: Optional[str] = None,
    current_handoff_team: Optional[str] = None,
    preset_code: Optional[str] = None,
    accepted_by: Optional[str] = None,
    action_batch_id: Optional[str] = None,
    acceptance_action: Optional[str] = None,
    acceptance_status: Optional[str] = None,
    selection_view_id: Optional[str] = None,
    selection_mode: Optional[str] = None,
    follow_through_status: Optional[str] = None,
    action_origin: Optional[str] = None,
    queue_type: Optional[str] = None,
    open_only: bool = False,
    preview_limit: int = 50,
    review_limit: int = 10,
    handoff_limit: int = 20,
    history_limit: int = 50,
    trend_days: int = 14,
    forecast_window_days: int = 7,
    sort_by: str = "recent",
) -> Dict[str, str]:
    query = {
        "vendor_id": vendor_id,
        "responsible_actor": responsible_actor,
        "responsible_team": responsible_team,
        "on_call_owner": on_call_owner,
        "on_call_team": on_call_team,
        "current_handoff_owner": current_handoff_owner,
        "current_handoff_team": current_handoff_team,
        "preset_code": preset_code,
        "accepted_by": accepted_by,
        "action_batch_id": action_batch_id,
        "acceptance_action": acceptance_action,
        "acceptance_status": acceptance_status,
        "selection_view_id": selection_view_id,
        "selection_mode": selection_mode,
        "follow_through_status": follow_through_status,
        "action_origin": action_origin,
        "queue_type": queue_type,
        "open_only": open_only,
        "activity_date": activity_date,
        "preview_limit": preview_limit,
        "review_limit": review_limit,
        "handoff_limit": handoff_limit,
        "history_limit": history_limit,
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
        "sort_by": sort_by,
    }
    return {
        "governance_review_handoff_acceptance_follow_through_burndown": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                query,
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_opened": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                {
                    **query,
                    "activity_kind": "opened",
                },
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_opened_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                {
                    **query,
                    "activity_kind": "opened",
                },
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_closed": (
            build_governance_scoped_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                {
                    **query,
                    "activity_kind": "closed",
                },
            )
        ),
        "governance_review_handoff_acceptance_follow_through_burndown_closed_export": (
            build_governance_scoped_export_path(
                "governance_review_handoff_acceptance_follow_through_burndown",
                {
                    **query,
                    "activity_kind": "closed",
                },
            )
        ),
    }


def build_governance_queue_row_urls(
    *,
    queue_type: str,
    consumer_urls: Optional[Mapping[str, str]] = None,
    order_id: Optional[str] = None,
    disposition_event_id: Optional[str] = None,
) -> Dict[str, str]:
    common = {
        "governance_action": governance_discoverability_path("governance_action"),
        "governance_burndown": governance_discoverability_path("governance_burndown"),
        "governance_correlation": governance_discoverability_path("governance_correlation"),
        "governance_sla_board": governance_discoverability_path("governance_sla_board"),
        "governance_history": governance_discoverability_path("governance_history"),
    }
    if queue_type == "approval_debt":
        if not order_id:
            return {}
        return {
            **dict(consumer_urls or {}),
            **common,
            "approval_board": (
                f"/api/v1/subcontracting/orders/{order_id}/return-disposition-approval-board"
            ),
            "approval_assign": (
                f"/api/v1/subcontracting/orders/{order_id}/return-dispositions/{disposition_event_id}/assign"
                if disposition_event_id
                else None
            ),
        }
    if queue_type == "cleanup_debt":
        return {
            **common,
            "role_mappings": governance_discoverability_path("role_mappings"),
            "cleanup_policy_board": governance_discoverability_path(
                "cleanup_policy_board"
            ),
            "cleanup_apply_preview": governance_discoverability_path(
                "cleanup_apply_preview"
            ),
        }
    if queue_type == "rollback_alert":
        return {
            **dict(consumer_urls or {}),
            **common,
            "rollback_burndown": governance_discoverability_path("rollback_burndown"),
            "rollback_board": governance_discoverability_path("rollback_board"),
            "alert_assign": governance_discoverability_path("alert_assign"),
            "alert_control": governance_discoverability_path("alert_control"),
        }
    return {}


def build_governance_preset_row_urls(
    *,
    effective_filters: Mapping[str, Any],
    preset_query: Mapping[str, Any],
    preview_limit: int,
) -> Dict[str, str]:
    acceptance_query = build_governance_window_query(
        preset_query,
        review_limit=preview_limit,
        handoff_limit=preview_limit,
        history_limit=preview_limit,
        sort_by="priority",
    )
    history_query = build_governance_window_query(
        preset_query,
        review_limit=preview_limit,
        handoff_limit=preview_limit,
        history_limit=preview_limit,
    )
    return {
        "governance_inbox": build_governance_scoped_path(
            "governance_inbox",
            effective_filters,
        ),
        "governance_export": build_governance_scoped_export_path(
            "governance_inbox",
            effective_filters,
        ),
        "governance_action": governance_discoverability_path("governance_action"),
        "governance_review_handoff_accept": governance_discoverability_path(
            "governance_review_handoff_accept"
        ),
        "governance_review_handoff_acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_history": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_history",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            acceptance_query,
        ),
        "governance_review_digest": build_governance_scoped_path(
            "governance_review_digest",
            preset_query,
        ),
        "governance_review_handoff": build_governance_scoped_path(
            "governance_review_handoff",
            preset_query,
        ),
        "governance_review_handoff_history": build_governance_scoped_path(
            "governance_review_handoff_history",
            history_query,
        ),
        "governance_burndown": build_governance_scoped_path(
            "governance_burndown",
            effective_filters,
        ),
        "governance_correlation": build_governance_scoped_path(
            "governance_correlation",
            effective_filters,
        ),
        "governance_correlation_preset": build_governance_scoped_path(
            "governance_correlation_presets",
            preset_query,
        ),
        "governance_history": build_governance_scoped_path(
            "governance_history",
            effective_filters,
        ),
    }


def build_governance_correlation_preset_row_urls(
    *,
    effective_filters: Mapping[str, Any],
    correlation_filters: Mapping[str, Any],
    preset_query: Mapping[str, Any],
    preview_limit: int,
    trend_days: int,
    forecast_window_days: int,
) -> Dict[str, str]:
    handoff_query = build_governance_window_query(
        preset_query,
        review_limit=preview_limit,
        handoff_limit=preview_limit,
    )
    history_query = build_governance_window_query(
        preset_query,
        review_limit=preview_limit,
        handoff_limit=preview_limit,
        history_limit=preview_limit,
    )
    acceptance_query = build_governance_window_query(
        preset_query,
        review_limit=preview_limit,
        handoff_limit=preview_limit,
        history_limit=preview_limit,
        sort_by="priority",
    )
    analytics_query = {
        **dict(correlation_filters),
        "trend_days": trend_days,
        "forecast_window_days": forecast_window_days,
    }
    return {
        "governance_correlation_preset": build_governance_scoped_path(
            "governance_correlation_presets",
            preset_query,
        ),
        "governance_review_digest": build_governance_scoped_path(
            "governance_review_digest",
            preset_query,
        ),
        "governance_review_handoff": build_governance_scoped_path(
            "governance_review_handoff",
            handoff_query,
        ),
        "governance_review_handoff_history": build_governance_scoped_path(
            "governance_review_handoff_history",
            history_query,
        ),
        "governance_review_handoff_acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_history": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_history",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            acceptance_query,
        ),
        "governance_inbox": build_governance_scoped_path(
            "governance_inbox",
            effective_filters,
        ),
        "governance_correlation": build_governance_scoped_path(
            "governance_correlation",
            analytics_query,
        ),
        "governance_burndown": build_governance_scoped_path(
            "governance_burndown",
            analytics_query,
        ),
        "governance_sla_board": build_governance_scoped_path(
            "governance_sla_board",
            effective_filters,
        ),
        "governance_history": build_governance_scoped_path(
            "governance_history",
            effective_filters,
        ),
    }


def build_governance_review_handoff_row_urls(
    *,
    digest_query: Mapping[str, Any],
    history_query: Mapping[str, Any],
    correlation_query: Mapping[str, Any],
    handoff_limit: int,
) -> Dict[str, str]:
    acceptance_query = build_governance_window_query(
        digest_query,
        handoff_limit=handoff_limit,
        history_limit=handoff_limit,
        sort_by="priority",
    )
    handoff_history_query = build_governance_window_query(
        digest_query,
        handoff_limit=handoff_limit,
        history_limit=handoff_limit,
    )
    return {
        "governance_review_digest": build_governance_scoped_path(
            "governance_review_digest",
            digest_query,
        ),
        "governance_review_handoff_accept": governance_discoverability_path(
            "governance_review_handoff_accept"
        ),
        "governance_review_handoff_acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_history": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_history",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            acceptance_query,
        ),
        "governance_review_handoff_history": build_governance_scoped_path(
            "governance_review_handoff_history",
            handoff_history_query,
        ),
        "governance_history": build_governance_scoped_path(
            "governance_history",
            history_query,
        ),
        "governance_correlation": build_governance_scoped_path(
            "governance_correlation",
            correlation_query,
        ),
        "governance_action": governance_discoverability_path("governance_action"),
    }


def build_governance_review_handoff_history_row_urls(
    *,
    handoff_query: Mapping[str, Any],
    acceptance_scope_query: Optional[Mapping[str, Any]] = None,
    digest_query: Mapping[str, Any],
    history_query: Mapping[str, Any],
    correlation_query: Mapping[str, Any],
    history_limit: int,
    sort_by: str,
) -> Dict[str, str]:
    acceptance_query_source = dict(acceptance_scope_query or handoff_query)
    acceptance_query = build_governance_window_query(
        acceptance_query_source,
        history_limit=history_limit,
        sort_by=sort_by,
    )
    entry_efficiency_query = build_governance_window_query(
        acceptance_query_source,
        history_limit=history_limit,
        sort_by="recent",
    )
    return {
        "governance_review_handoff": build_governance_scoped_path(
            "governance_review_handoff",
            handoff_query,
        ),
        "governance_review_handoff_accept": governance_discoverability_path(
            "governance_review_handoff_accept"
        ),
        "governance_review_handoff_acceptance_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_entry_efficiency": build_governance_scoped_path(
            "governance_review_handoff_acceptance_entry_efficiency",
            entry_efficiency_query,
        ),
        "governance_review_handoff_acceptance_follow_through_digest": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_digest",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_history": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_history",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_follow_through_burndown": build_governance_scoped_path(
            "governance_review_handoff_acceptance_follow_through_burndown",
            acceptance_query,
        ),
        "governance_review_handoff_acceptance_trends": build_governance_scoped_path(
            "governance_review_handoff_acceptance_trends",
            acceptance_query,
        ),
        "governance_review_digest": build_governance_scoped_path(
            "governance_review_digest",
            digest_query,
        ),
        "governance_history": build_governance_scoped_path(
            "governance_history",
            history_query,
        ),
        "governance_correlation": build_governance_scoped_path(
            "governance_correlation",
            correlation_query,
        ),
        "governance_action": governance_discoverability_path("governance_action"),
    }
