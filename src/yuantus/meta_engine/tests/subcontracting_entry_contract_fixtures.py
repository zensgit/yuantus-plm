"""Shared test fixtures for governance entry contracts."""
from __future__ import annotations

from typing import Any, Dict, Optional

from yuantus.meta_engine.subcontracting.entry_contract import (
    build_recommended_entry_contract,
    summarize_recommended_entry_contract,
    summarize_recommended_entry_default_action,
    summarize_recommended_entry_guidance,
    summarize_recommended_entry_panel,
    summarize_recommended_entry_preset,
)


def build_entry_contract_bundle(
    *,
    entry_path: str,
    preset_code: str,
    action: str,
    queue_type: Optional[str],
    selection_mode: Optional[str] = None,
    view_id: Optional[str] = None,
) -> Dict[str, Any]:
    if entry_path == "review_handoff_acceptance":
        panel = {
            "entry_path": entry_path,
            "view": "review_handoff",
            "endpoint": "/api/v1/subcontracting/governance-inbox/review-handoff",
            "method": "GET",
            "query": {"preset_code": preset_code},
        }
        default_action = {
            "entry_path": entry_path,
            "action_origin": entry_path,
            "action": action,
            "queue_type": queue_type,
            "selection_mode": selection_mode,
            "endpoint": "/api/v1/subcontracting/governance-inbox/review-handoff/accept",
            "method": "POST",
            "body": {
                "preset_code": preset_code,
                "selection_mode": selection_mode or "policy",
                **({"view_id": view_id} if view_id else {}),
            },
        }
    else:
        panel = {
            "entry_path": entry_path,
            "view": "governance_inbox",
            "endpoint": "/api/v1/subcontracting/governance-inbox",
            "method": "GET",
            "query": {"preset_code": preset_code, "queue_type": queue_type},
        }
        default_action = {
            "entry_path": entry_path,
            "action_origin": entry_path,
            "action": action,
            "queue_type": queue_type,
            "selection_mode": None,
            "endpoint": "/api/v1/subcontracting/governance-inbox/action",
            "method": "POST",
            "body": {
                "queue_type": queue_type,
                "action": action,
            },
        }
    preset = {
        "code": preset_code,
        "endpoint": "/api/v1/subcontracting/governance-inbox/presets",
        "method": "GET",
        "query": {"preset_code": preset_code},
    }
    contract = build_recommended_entry_contract(
        entry_path=entry_path,
        preset_code=preset_code,
        preset=preset,
        panel=panel,
        default_action=default_action,
        selection_mode=selection_mode,
        entry_efficiency_query={
            "preset_code": preset_code,
            **({"selection_view_id": view_id} if view_id else {}),
            **({"selection_mode": selection_mode} if selection_mode else {}),
        },
        follow_through_burndown_query={"preset_code": preset_code},
    )
    payload = {
        "recommended_entry_preset": preset,
        "recommended_entry_panel": panel,
        "recommended_entry_default_action": default_action,
        "recommended_entry_guidance": {
            "schema_version": contract["schema_version"],
            "entry_path": contract["entry_path"],
            "preset_code": contract["preset_code"],
            "preset": dict(contract.get("preset") or {}),
            "panel": dict(contract.get("panel") or {}),
            "default_action": dict(contract.get("default_action") or {}),
        },
        "recommended_entry_contract": contract,
    }
    payload["summary"] = {
        "recommended_entry_preset": summarize_recommended_entry_preset(payload),
        "recommended_entry_panel": summarize_recommended_entry_panel(payload),
        "recommended_entry_default_action": summarize_recommended_entry_default_action(
            payload
        ),
        "recommended_entry_guidance": summarize_recommended_entry_guidance(payload),
        "recommended_entry_contract": summarize_recommended_entry_contract(payload),
    }
    return payload


def build_review_handoff_entry_contract_bundle(
    *,
    preset_code: str = "cleanup_follow_through",
    action: str = "accept",
    queue_type: str = "cleanup_debt",
    selection_mode: str = "policy",
    view_id: Optional[str] = None,
) -> Dict[str, Any]:
    return build_entry_contract_bundle(
        entry_path="review_handoff_acceptance",
        preset_code=preset_code,
        action=action,
        queue_type=queue_type,
        selection_mode=selection_mode,
        view_id=view_id,
    )


def build_governance_inbox_entry_contract_bundle(
    *,
    preset_code: str = "rollback_on_call",
    action: str = "acknowledge",
    queue_type: str = "rollback_alert",
) -> Dict[str, Any]:
    return build_entry_contract_bundle(
        entry_path="governance_inbox",
        preset_code=preset_code,
        action=action,
        queue_type=queue_type,
    )
