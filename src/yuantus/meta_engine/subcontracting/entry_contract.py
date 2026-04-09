"""Shared governance entry contract builders and serializers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_analysis_request(*, endpoint: str, query: Dict[str, Any]) -> Dict[str, Any]:
    normalized_query = dict(query or {})
    return {
        "endpoint": endpoint,
        "method": "GET",
        "query": normalized_query,
        "export": {
            "endpoint": f"{endpoint}/export",
            "method": "GET",
            "query": {
                **normalized_query,
                "format": "json",
            },
        },
    }


def build_recommended_entry_contract(
    *,
    entry_path: Optional[str],
    preset_code: Optional[str],
    preset: Optional[Dict[str, Any]],
    panel: Optional[Dict[str, Any]],
    default_action: Optional[Dict[str, Any]],
    selection_mode: Optional[str],
    entry_efficiency_query: Dict[str, Any],
    follow_through_burndown_query: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    normalized_entry_path = str(entry_path or "").strip() or None
    if not normalized_entry_path:
        return None
    normalized_preset = dict(preset or {})
    normalized_panel = dict(panel or {})
    normalized_default_action = dict(default_action or {})
    return {
        "schema_version": "v1",
        "entry_path": normalized_entry_path,
        "preset_code": preset_code,
        "preset": normalized_preset,
        "panel": normalized_panel,
        "default_action": normalized_default_action,
        "resolver": {
            "sequence": (
                ["prepare_request", "open_request", "default_action_request"]
                if normalized_preset
                else ["open_request", "default_action_request"]
            ),
            "supports_selection": (
                normalized_entry_path == "review_handoff_acceptance"
            ),
            "selection_mode": selection_mode,
            "prepare_request": normalized_preset,
            "open_request": normalized_panel,
            "default_action_request": normalized_default_action,
        },
        "analysis": {
            "entry_efficiency": build_analysis_request(
                endpoint="/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency",
                query=entry_efficiency_query,
            ),
            "follow_through_burndown": build_analysis_request(
                endpoint="/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown",
                query=follow_through_burndown_query,
            ),
        },
    }


def summarize_recommended_entry_preset(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    recommended_entry_preset = dict(payload.get("recommended_entry_preset") or {})
    if not recommended_entry_preset:
        return None
    return {
        "code": recommended_entry_preset.get("code"),
        "endpoint": recommended_entry_preset.get("endpoint"),
        "method": recommended_entry_preset.get("method"),
    }


def summarize_recommended_entry_panel(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    recommended_entry_panel = dict(payload.get("recommended_entry_panel") or {})
    if not recommended_entry_panel:
        return None
    return {
        "entry_path": recommended_entry_panel.get("entry_path"),
        "view": recommended_entry_panel.get("view"),
        "endpoint": recommended_entry_panel.get("endpoint"),
        "method": recommended_entry_panel.get("method"),
    }


def summarize_recommended_entry_default_action(
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    recommended_entry_default_action = dict(
        payload.get("recommended_entry_default_action") or {}
    )
    if not recommended_entry_default_action:
        return None
    return {
        "entry_path": recommended_entry_default_action.get("entry_path"),
        "action_origin": recommended_entry_default_action.get("action_origin"),
        "action": recommended_entry_default_action.get("action"),
        "queue_type": recommended_entry_default_action.get("queue_type"),
        "selection_mode": recommended_entry_default_action.get("selection_mode"),
        "endpoint": recommended_entry_default_action.get("endpoint"),
        "method": recommended_entry_default_action.get("method"),
    }


def summarize_recommended_entry_guidance(
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    recommended_entry_guidance = dict(payload.get("recommended_entry_guidance") or {})
    if not recommended_entry_guidance:
        return None
    return {
        "schema_version": recommended_entry_guidance.get("schema_version"),
        "entry_path": recommended_entry_guidance.get("entry_path"),
        "preset_code": recommended_entry_guidance.get("preset_code"),
        "preset": dict(recommended_entry_guidance.get("preset") or {}),
        "panel": dict(recommended_entry_guidance.get("panel") or {}),
        "default_action": dict(recommended_entry_guidance.get("default_action") or {}),
    }


def summarize_recommended_entry_contract(
    payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    recommended_entry_contract = dict(
        payload.get("recommended_entry_contract")
        or payload.get("recommended_entry_guidance")
        or {}
    )
    if not recommended_entry_contract:
        return None
    contract_resolver = dict(recommended_entry_contract.get("resolver") or {})
    contract_analysis = dict(recommended_entry_contract.get("analysis") or {})
    contract_prepare_request = dict(contract_resolver.get("prepare_request") or {})
    contract_open_request = dict(contract_resolver.get("open_request") or {})
    contract_default_action_request = dict(
        contract_resolver.get("default_action_request") or {}
    )
    contract_entry_efficiency = dict(contract_analysis.get("entry_efficiency") or {})
    contract_follow_through_burndown = dict(
        contract_analysis.get("follow_through_burndown") or {}
    )
    return {
        "schema_version": recommended_entry_contract.get("schema_version"),
        "entry_path": recommended_entry_contract.get("entry_path"),
        "preset_code": recommended_entry_contract.get("preset_code"),
        "resolver": {
            "sequence": list(contract_resolver.get("sequence") or []),
            "supports_selection": contract_resolver.get("supports_selection"),
            "selection_mode": contract_resolver.get("selection_mode"),
            "prepare_request": (
                {
                    "endpoint": contract_prepare_request.get("endpoint"),
                    "method": contract_prepare_request.get("method"),
                }
                if contract_prepare_request
                else None
            ),
            "open_request": (
                {
                    "endpoint": contract_open_request.get("endpoint"),
                    "method": contract_open_request.get("method"),
                    "view": contract_open_request.get("view"),
                }
                if contract_open_request
                else None
            ),
            "default_action_request": (
                {
                    "endpoint": contract_default_action_request.get("endpoint"),
                    "method": contract_default_action_request.get("method"),
                    "action": contract_default_action_request.get("action"),
                    "queue_type": contract_default_action_request.get("queue_type"),
                    "selection_mode": contract_default_action_request.get(
                        "selection_mode"
                    ),
                }
                if contract_default_action_request
                else None
            ),
        },
        "analysis": {
            "entry_efficiency": (
                {
                    "endpoint": contract_entry_efficiency.get("endpoint"),
                    "method": contract_entry_efficiency.get("method"),
                    "export_endpoint": (
                        dict(contract_entry_efficiency.get("export") or {}).get(
                            "endpoint"
                        )
                    ),
                    "export_method": (
                        dict(contract_entry_efficiency.get("export") or {}).get(
                            "method"
                        )
                    ),
                }
                if contract_entry_efficiency
                else None
            ),
            "follow_through_burndown": (
                {
                    "endpoint": contract_follow_through_burndown.get("endpoint"),
                    "method": contract_follow_through_burndown.get("method"),
                    "export_endpoint": (
                        dict(contract_follow_through_burndown.get("export") or {}).get(
                            "endpoint"
                        )
                    ),
                    "export_method": (
                        dict(contract_follow_through_burndown.get("export") or {}).get(
                            "method"
                        )
                    ),
                }
                if contract_follow_through_burndown
                else None
            ),
        },
    }


def render_recommended_entry_markdown_lines(payload: Dict[str, Any]) -> List[str]:
    recommended_entry_guidance = summarize_recommended_entry_guidance(payload) or {}
    recommended_entry_contract = summarize_recommended_entry_contract(payload) or {}
    recommended_entry_panel = summarize_recommended_entry_panel(payload) or {}
    recommended_entry_default_action = (
        summarize_recommended_entry_default_action(payload) or {}
    )
    contract_analysis = dict(recommended_entry_contract.get("analysis") or {})
    return [
        f"- recommended_entry_guidance_schema_version: `{recommended_entry_guidance.get('schema_version')}`",
        f"- recommended_entry_contract_schema_version: `{recommended_entry_contract.get('schema_version')}`",
        f"- recommended_entry_panel_endpoint: `{recommended_entry_panel.get('endpoint')}`",
        f"- recommended_entry_default_action: `{recommended_entry_default_action.get('action')}`",
        f"- recommended_entry_default_action_endpoint: `{recommended_entry_default_action.get('endpoint')}`",
        f"- recommended_entry_contract_entry_efficiency_export_endpoint: `{dict(contract_analysis.get('entry_efficiency') or {}).get('export_endpoint')}`",
        f"- recommended_entry_contract_follow_through_burndown_export_endpoint: `{dict(contract_analysis.get('follow_through_burndown') or {}).get('export_endpoint')}`",
    ]
