from yuantus.meta_engine.subcontracting.entry_contract import (
    build_recommended_entry_contract,
    render_recommended_entry_markdown_lines,
    summarize_recommended_entry_contract,
)


def test_build_recommended_entry_contract_includes_resolver_and_analysis():
    contract = build_recommended_entry_contract(
        entry_path="review_handoff_acceptance",
        preset_code="cleanup_follow_through",
        preset={
            "code": "cleanup_follow_through",
            "endpoint": "/api/v1/subcontracting/governance-inbox/presets",
            "method": "GET",
        },
        panel={
            "entry_path": "review_handoff_acceptance",
            "view": "review_handoff",
            "endpoint": "/api/v1/subcontracting/governance-inbox/review-handoff",
            "method": "GET",
        },
        default_action={
            "entry_path": "review_handoff_acceptance",
            "action_origin": "review_handoff_acceptance",
            "action": "accept",
            "endpoint": "/api/v1/subcontracting/governance-inbox/review-handoff/accept",
            "method": "POST",
        },
        selection_mode="policy",
        entry_efficiency_query={"preset_code": "cleanup_follow_through"},
        follow_through_burndown_query={"preset_code": "cleanup_follow_through"},
    )

    assert contract["schema_version"] == "v1"
    assert contract["resolver"]["sequence"] == [
        "prepare_request",
        "open_request",
        "default_action_request",
    ]
    assert contract["resolver"]["default_action_request"]["action"] == "accept"
    assert (
        contract["analysis"]["entry_efficiency"]["export"]["endpoint"]
        == "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-entry-efficiency/export"
    )
    assert (
        contract["analysis"]["follow_through_burndown"]["export"]["endpoint"]
        == "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown/export"
    )


def test_summarize_and_markdown_lines_share_contract_shape():
    payload = {
        "recommended_entry_contract": build_recommended_entry_contract(
            entry_path="governance_inbox",
            preset_code="rollback_on_call",
            preset={
                "code": "rollback_on_call",
                "endpoint": "/api/v1/subcontracting/governance-inbox/presets",
                "method": "GET",
            },
            panel={
                "entry_path": "governance_inbox",
                "view": "governance_inbox",
                "endpoint": "/api/v1/subcontracting/governance-inbox",
                "method": "GET",
            },
            default_action={
                "entry_path": "governance_inbox",
                "action_origin": "governance_inbox",
                "action": "acknowledge",
                "queue_type": "rollback_alert",
                "endpoint": "/api/v1/subcontracting/governance-inbox/action",
                "method": "POST",
            },
            selection_mode=None,
            entry_efficiency_query={"preset_code": "rollback_on_call"},
            follow_through_burndown_query={"preset_code": "rollback_on_call"},
        ),
        "recommended_entry_guidance": {
            "schema_version": "v1",
            "entry_path": "governance_inbox",
            "preset_code": "rollback_on_call",
            "panel": {
                "endpoint": "/api/v1/subcontracting/governance-inbox",
                "method": "GET",
            },
            "default_action": {
                "endpoint": "/api/v1/subcontracting/governance-inbox/action",
                "method": "POST",
                "action": "acknowledge",
            },
        },
        "recommended_entry_panel": {
            "endpoint": "/api/v1/subcontracting/governance-inbox",
        },
        "recommended_entry_default_action": {
            "endpoint": "/api/v1/subcontracting/governance-inbox/action",
            "action": "acknowledge",
        },
    }

    summary = summarize_recommended_entry_contract(payload)
    markdown_lines = render_recommended_entry_markdown_lines(payload)

    assert summary["resolver"]["default_action_request"]["endpoint"] == (
        "/api/v1/subcontracting/governance-inbox/action"
    )
    assert summary["analysis"]["follow_through_burndown"]["export_endpoint"] == (
        "/api/v1/subcontracting/governance-inbox/review-handoff/acceptance-follow-through-burndown/export"
    )
    assert any("recommended_entry_contract_schema_version" in line for line in markdown_lines)
    assert any(
        "/api/v1/subcontracting/governance-inbox/action" in line
        for line in markdown_lines
    )
