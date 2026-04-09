from __future__ import annotations

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.models.eco import ECOState
from yuantus.meta_engine.services.eco_service import ECOApprovalService, ECOService


def test_move_to_stage_runs_activity_gate_and_custom_actions_hooks():
    session = MagicMock()
    stage = SimpleNamespace(id="stage-2", approval_type="mandatory")
    session.query.return_value.get.return_value = stage
    session.get.side_effect = lambda model, value: (
        SimpleNamespace(roles=[SimpleNamespace(name="planner"), SimpleNamespace(name="qa")])
        if value == 1
        else None
    )

    service = ECOService(session)
    service.permission_service.check_permission = MagicMock()
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.DRAFT.value,
        stage_id="stage-1",
        priority="high",
        updated_at=None,
    )
    service.get_eco = MagicMock(return_value=eco)
    service._ensure_activity_gate_ready = MagicMock()
    service._run_custom_actions = MagicMock()
    service._apply_stage_sla = MagicMock()
    service._notify_stage_assignment = MagicMock()
    service._enqueue_eco_updated = MagicMock()

    result = service.move_to_stage("eco-1", "stage-2", user_id=1)

    assert result is eco
    assert eco.stage_id == "stage-2"
    assert eco.state == ECOState.PROGRESS.value
    service._ensure_activity_gate_ready.assert_called_once_with("eco-1")
    assert service._run_custom_actions.call_count == 2
    before = service._run_custom_actions.call_args_list[0].kwargs
    after = service._run_custom_actions.call_args_list[1].kwargs
    assert before["trigger_phase"] == "before"
    assert before["from_state"] == ECOState.DRAFT.value
    assert before["to_state"] == ECOState.PROGRESS.value
    assert before["context"] == {"stage_id": "stage-2", "actor_roles": ["planner", "qa"]}
    assert after["trigger_phase"] == "after"
    assert after["to_state"] == ECOState.PROGRESS.value
    assert after["context"] == {"stage_id": "stage-2", "actor_roles": ["planner", "qa"]}


def test_action_apply_runs_activity_gate_and_custom_actions_hooks():
    session = MagicMock()
    service = ECOService(session)
    service.permission_service.check_permission = MagicMock()
    service._ensure_activity_gate_ready = MagicMock()
    service._run_custom_actions = MagicMock()
    service._enqueue_eco_updated = MagicMock()
    service.check_rebase_needed = MagicMock(return_value=False)
    service.detect_rebase_conflicts = MagicMock(return_value=[])

    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.APPROVED.value,
        product_id="item-1",
        target_version_id="v-2",
        product_version_after=None,
        kanban_state="normal",
        priority="urgent",
        updated_at=None,
    )
    product = SimpleNamespace(
        id="item-1",
        current_version_id="v-1",
        properties={"rev": "A"},
        updated_at=None,
    )
    current_version = SimpleNamespace(id="v-1", is_current=True)
    target_version = SimpleNamespace(
        id="v-2",
        is_current=False,
        properties={"rev": "B"},
        version_label="B",
    )

    def _get(model, value):
        if getattr(model, "__name__", "") == "RBACUser" and value == 1:
            return SimpleNamespace(roles=[SimpleNamespace(name="approver")])
        if value == "item-1":
            return product
        return None

    session.get.side_effect = _get

    service.get_eco = MagicMock(return_value=eco)
    service.version_service.get_version = MagicMock(
        side_effect=lambda version_id: current_version if version_id == "v-1" else target_version
    )

    with patch(
        "yuantus.meta_engine.services.eco_service.VersionFileService"
    ) as version_file_service_cls:
        version_file_service_cls.return_value.sync_version_files_to_item.return_value = None
        ok = service.action_apply("eco-1", user_id=1)

    assert ok is True
    assert eco.state == ECOState.DONE.value
    assert eco.kanban_state == "done"
    assert product.current_version_id == "v-2"
    service._ensure_activity_gate_ready.assert_called_once_with("eco-1")
    assert service._run_custom_actions.call_count == 2
    before = service._run_custom_actions.call_args_list[0].kwargs
    after = service._run_custom_actions.call_args_list[1].kwargs
    assert before["trigger_phase"] == "before"
    assert before["from_state"] == ECOState.APPROVED.value
    assert before["to_state"] == ECOState.DONE.value
    assert before["context"] == {"actor_roles": ["approver"]}
    assert after["trigger_phase"] == "after"
    assert after["to_state"] == ECOState.DONE.value
    assert after["context"] == {"actor_roles": ["approver"]}


def test_run_custom_actions_includes_runtime_scope_context():
    session = MagicMock()
    service = ECOService(session)
    eco = SimpleNamespace(
        id="eco-1",
        stage_id="stage-2",
        priority="urgent",
        eco_type="document",
        product_id="item-1",
    )

    with patch(
        "yuantus.meta_engine.services.parallel_tasks_service.WorkflowCustomActionService"
    ) as service_cls:
        service._run_custom_actions(
            eco=eco,
            from_state="draft",
            to_state="progress",
            trigger_phase="before",
            context={"workflow_map_id": "wf-map-1"},
        )

    service_cls.return_value.evaluate_transition.assert_called_once_with(
        object_id="eco-1",
        target_object="ECO",
        from_state="draft",
        to_state="progress",
        trigger_phase="before",
        context={
            "source": "eco_service",
            "eco_id": "eco-1",
            "stage_id": "stage-2",
            "eco_priority": "urgent",
            "eco_type": "document",
            "product_id": "item-1",
            "workflow_map_id": "wf-map-1",
        },
    )


def test_compute_bom_changes_supports_compare_mode():
    session = MagicMock()
    service = ECOService(session)
    eco = SimpleNamespace(
        id="eco-1",
        product_id="item-parent-1",
        source_version_id="v-1",
        target_version_id="v-2",
    )
    service.get_eco = MagicMock(return_value=eco)
    service.get_bom_diff = MagicMock(
        return_value={
            "compare_mode": "summarized",
            "added": [
                {
                    "relationship_id": "rel-add-1",
                    "parent_id": "item-parent-1",
                    "child_id": "item-child-add-1",
                    "properties": {"quantity": 3, "uom": "EA"},
                }
            ],
            "removed": [
                {
                    "relationship_id": "rel-remove-1",
                    "parent_id": "item-parent-1",
                    "child_id": "item-child-remove-1",
                    "properties": {"quantity": 1, "uom": "EA"},
                }
            ],
            "changed": [
                {
                    "relationship_id": "rel-update-1",
                    "parent_id": "item-parent-1",
                    "child_id": "item-child-update-1",
                    "before_line": {"quantity": 2, "uom": "EA"},
                    "after_line": {"quantity": 5, "uom": "EA"},
                }
            ],
        }
    )
    session.get.side_effect = lambda model, item_id: (
        SimpleNamespace(id=item_id) if item_id else None
    )

    changes = service.compute_bom_changes("eco-1", compare_mode="summarized")

    service.get_bom_diff.assert_called_once_with(
        "eco-1",
        max_levels=1,
        compare_mode="summarized",
    )
    assert [change.change_type for change in changes] == ["add", "remove", "update"]
    assert changes[0].relationship_item_id == "rel-add-1"
    assert changes[0].new_properties == {"quantity": 3, "uom": "EA"}
    assert changes[1].relationship_item_id == "rel-remove-1"
    assert changes[1].old_properties == {"quantity": 1, "uom": "EA"}
    assert changes[2].relationship_item_id == "rel-update-1"
    assert changes[2].old_properties == {"quantity": 2, "uom": "EA"}
    assert changes[2].new_properties == {"quantity": 5, "uom": "EA"}


def test_action_suspend_runs_custom_action_hooks_and_marks_blocked():
    session = MagicMock()
    session.get.side_effect = lambda model, value: (
        SimpleNamespace(roles=[SimpleNamespace(name="planner")])
        if getattr(model, "__name__", "") == "RBACUser" and value == 1
        else None
    )

    service = ECOService(session)
    service.permission_service.check_permission = MagicMock()
    service._run_custom_actions = MagicMock()
    service._enqueue_eco_updated = MagicMock()
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.PROGRESS.value,
        stage_id="stage-1",
        priority="normal",
        eco_type="bom",
        product_id="item-1",
        kanban_state="normal",
        description="Needs review",
        approval_deadline=None,
        updated_at=None,
    )
    service.get_eco = MagicMock(return_value=eco)

    result = service.action_suspend("eco-1", user_id=1, reason="awaiting vendor input")

    assert result is eco
    assert eco.state == ECOState.SUSPENDED.value
    assert eco.kanban_state == "blocked"
    assert "[SUSPENDED] awaiting vendor input" in (eco.description or "")
    assert service._run_custom_actions.call_count == 2
    before = service._run_custom_actions.call_args_list[0].kwargs
    after = service._run_custom_actions.call_args_list[1].kwargs
    assert before["from_state"] == ECOState.PROGRESS.value
    assert before["to_state"] == ECOState.SUSPENDED.value
    assert before["context"] == {
        "reason": "awaiting vendor input",
        "actor_roles": ["planner"],
    }
    assert after["to_state"] == ECOState.SUSPENDED.value
    assert after["context"] == {
        "reason": "awaiting vendor input",
        "actor_roles": ["planner"],
    }


def test_action_unsuspend_defaults_to_progress_and_reapplies_stage_sla():
    session = MagicMock()
    stage = SimpleNamespace(id="stage-1", approval_type="mandatory", sla_hours=24)

    def _get(model, value):
        if getattr(model, "__name__", "") == "RBACUser" and value == 1:
            return SimpleNamespace(roles=[SimpleNamespace(name="planner")])
        if getattr(model, "__name__", "") == "ECOStage" and value == "stage-1":
            return stage
        return None

    session.get.side_effect = _get

    service = ECOService(session)
    service.permission_service.check_permission = MagicMock()
    service._run_custom_actions = MagicMock()
    service._enqueue_eco_updated = MagicMock()
    service._apply_stage_sla = MagicMock()
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.SUSPENDED.value,
        stage_id="stage-1",
        priority="normal",
        eco_type="bom",
        product_id="item-1",
        kanban_state="blocked",
        approval_deadline=None,
        updated_at=None,
    )
    service.get_eco = MagicMock(return_value=eco)

    result = service.action_unsuspend("eco-1", user_id=1)

    assert result is eco
    assert eco.state == ECOState.PROGRESS.value
    assert eco.kanban_state == "normal"
    service._apply_stage_sla.assert_called_once_with(eco, stage)
    assert service._run_custom_actions.call_count == 2
    before = service._run_custom_actions.call_args_list[0].kwargs
    after = service._run_custom_actions.call_args_list[1].kwargs
    assert before["from_state"] == ECOState.SUSPENDED.value
    assert before["to_state"] == ECOState.PROGRESS.value
    assert before["context"] == {
        "resume_state": ECOState.PROGRESS.value,
        "actor_roles": ["planner"],
    }
    assert after["to_state"] == ECOState.PROGRESS.value
    assert after["context"] == {
        "resume_state": ECOState.PROGRESS.value,
        "actor_roles": ["planner"],
    }


def test_move_to_stage_rejects_suspended_eco():
    session = MagicMock()
    service = ECOService(session)
    service.permission_service.check_permission = MagicMock()
    eco = SimpleNamespace(id="eco-1", state=ECOState.SUSPENDED.value, stage_id="stage-1")
    service.get_eco = MagicMock(return_value=eco)
    service._ensure_activity_gate_ready = MagicMock()

    with pytest.raises(ValueError, match="suspended"):
        service.move_to_stage("eco-1", "stage-2", user_id=1)

    service._ensure_activity_gate_ready.assert_not_called()


def test_action_new_revision_rejects_suspended_eco():
    session = MagicMock()
    service = ECOService(session)
    service.permission_service.check_permission = MagicMock()
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.SUSPENDED.value,
        product_id="item-1",
    )
    service.get_eco = MagicMock(return_value=eco)

    with pytest.raises(ValueError, match="suspended"):
        service.action_new_revision("eco-1", user_id=1)


@pytest.mark.parametrize(
    ("method_name", "kwargs"),
    [
        ("approve", {"comment": None}),
        ("reject", {"comment": "send back"}),
    ],
)
def test_approval_actions_reject_suspended_eco(method_name, kwargs):
    session = MagicMock()
    approval_service = ECOApprovalService(session)
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.SUSPENDED.value,
        stage_id="stage-1",
    )
    session.get.side_effect = lambda model, value: (
        eco if getattr(model, "__name__", "") == "ECO" and value == "eco-1" else None
    )

    with pytest.raises(ValueError, match="suspended"):
        getattr(approval_service, method_name)("eco-1", user_id=1, **kwargs)


def test_get_unsuspend_diagnostics_reports_activity_blockers():
    session = MagicMock()
    service = ECOService(session)
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.SUSPENDED.value,
        stage_id="stage-1",
    )
    stage = SimpleNamespace(id="stage-1", approval_type="mandatory")
    service.get_eco = MagicMock(return_value=eco)
    session.get.side_effect = lambda model, value: (
        stage if getattr(model, "__name__", "") == "ECOStage" and value == "stage-1" else None
    )
    service._ensure_activity_gate_ready = MagicMock(
        side_effect=ValueError("ECO activity blockers detected: act-1")
    )

    diagnostics = service.get_unsuspend_diagnostics("eco-1", user_id=1)

    assert diagnostics["ruleset_id"] == "default"
    assert [issue.code for issue in diagnostics["errors"]] == [
        "eco_activity_blockers_present"
    ]


def test_get_unsuspend_diagnostics_requires_complete_stage_for_approved_resume():
    session = MagicMock()
    service = ECOService(session)
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.SUSPENDED.value,
        stage_id="stage-1",
    )
    stage = SimpleNamespace(id="stage-1", approval_type="mandatory", min_approvals=1)
    service.get_eco = MagicMock(return_value=eco)
    session.get.side_effect = lambda model, value: (
        stage if getattr(model, "__name__", "") == "ECOStage" and value == "stage-1" else None
    )
    service._ensure_activity_gate_ready = MagicMock(return_value=None)

    with patch.object(
        ECOApprovalService,
        "check_stage_approvals_complete",
        return_value=False,
    ):
        diagnostics = service.get_unsuspend_diagnostics(
            "eco-1",
            user_id=1,
            resume_state=ECOState.APPROVED.value,
        )

    assert [issue.code for issue in diagnostics["errors"]] == [
        "eco_stage_approvals_incomplete"
    ]
