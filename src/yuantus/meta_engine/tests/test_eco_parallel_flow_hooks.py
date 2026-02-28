from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.models.eco import ECOState
from yuantus.meta_engine.services.eco_service import ECOService


def test_move_to_stage_runs_activity_gate_and_custom_actions_hooks():
    session = MagicMock()
    stage = SimpleNamespace(id="stage-2", approval_type="mandatory")
    session.query.return_value.get.return_value = stage

    service = ECOService(session)
    service.permission_service.check_permission = MagicMock()
    eco = SimpleNamespace(
        id="eco-1",
        state=ECOState.DRAFT.value,
        stage_id="stage-1",
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
    assert after["trigger_phase"] == "after"
    assert after["to_state"] == ECOState.PROGRESS.value


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

    service.get_eco = MagicMock(return_value=eco)
    session.get.return_value = product
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
    assert after["trigger_phase"] == "after"
    assert after["to_state"] == ECOState.DONE.value
