import pytest
from unittest.mock import MagicMock
from yuantus.meta_engine.workflow.service import WorkflowService
from yuantus.meta_engine.workflow.models import (
    WorkflowProcess,
    WorkflowActivity,
    WorkflowTask,
    WorkflowActivityInstance,
)
from yuantus.meta_engine.models.item import Item
from yuantus.security.rbac.models import RBACUser, RBACRole


class TestWorkflowIdentity:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    def test_assign_dynamic_creator(self, mock_session):
        service = WorkflowService(mock_session)

        # Setup Item with Creator
        # We need check for Item class in side_effect
        mock_item = Item(id="Item1", created_by_id=99)

        def get_side_effect(model, id):
            if model == Item:
                return mock_item
            return None

        mock_session.get.side_effect = get_side_effect

        process = WorkflowProcess(id="P1", item_id="Item1")
        activity = WorkflowActivity(
            id="A1",
            type="activity",
            assignee_type="dynamic",
            dynamic_identity="Creator",
            name="Review",
        )

        service._activate_activity(process, activity)

        # Verify Task created for user 99
        # calls[0] -> instance add
        # calls[1] -> task add (hopefully)
        assert mock_session.add.call_count >= 2
        task = mock_session.add.call_args_list[-1][0][0]
        assert isinstance(task, WorkflowTask)
        assert task.assigned_to_user_id == 99
        assert task.dynamic_identity == "Creator"

    def test_assign_dynamic_owner(self, mock_session):
        service = WorkflowService(mock_session)
        mock_item = Item(id="Item1", created_by_id=99, owner_id=101)

        def get_side_effect(model, id):
            if model == Item:
                return mock_item
            return None

        mock_session.get.side_effect = get_side_effect

        process = WorkflowProcess(id="P1", item_id="Item1")
        activity = WorkflowActivity(
            id="A1", type="activity", assignee_type="dynamic", dynamic_identity="Owner"
        )

        service._activate_activity(process, activity)

        task = mock_session.add.call_args_list[-1][0][0]
        assert isinstance(task, WorkflowTask)
        assert task.assigned_to_user_id == 101  # Owner
        assert task.dynamic_identity == "Owner"

    def test_assign_role(self, mock_session):
        service = WorkflowService(mock_session)
        process = WorkflowProcess(id="P1", item_id="Item1")
        activity = WorkflowActivity(
            id="A1",
            type="activity",
            assignee_type="role",
            role_id=5,
            name="Manager Review",
        )

        service._activate_activity(process, activity)

        task = mock_session.add.call_args_list[-1][0][0]
        assert isinstance(task, WorkflowTask)
        assert task.assigned_to_role_id == 5
        assert task.assigned_to_user_id is None  # No specific user yet

    def test_assign_direct_user(self, mock_session):
        service = WorkflowService(mock_session)
        process = WorkflowProcess(id="P1", item_id="Item1")
        activity = WorkflowActivity(
            id="A1", type="activity", assignee_type="user", user_id=77
        )

        service._activate_activity(process, activity)

        task = mock_session.add.call_args_list[-1][0][0]
        assert isinstance(task, WorkflowTask)
        assert task.assigned_to_user_id == 77
        assert task.assigned_to_role_id is None

    def test_vote_role_assignment_allowed(self, mock_session):
        service = WorkflowService(mock_session)
        # Prevent actual evaluation logic from running (not focus of this test)
        service._evaluate_activity = MagicMock()

        # Use real objects to avoid SA instrumentation errors
        activity = WorkflowActivity(id="A1")
        instance = WorkflowActivityInstance(id="Inst1")
        instance.activity = activity

        # Task assigned to Role 5
        task = WorkflowTask(
            id="T1", status="Pending", assigned_to_role_id=5, assigned_to_user_id=None
        )
        task.activity_instance = instance  # Real object assignment works fine

        # User has Role 5
        user = RBACUser(id=10, roles=[RBACRole(id=5), RBACRole(id=3)])

        def get_side_effect(model, id):
            if model == WorkflowTask:
                return task
            if model == RBACUser:
                return user
            return None

        mock_session.get.side_effect = get_side_effect

        # Mock query count for pending tasks (if _evaluate was called, but we mocked it)
        # Actually since we mocked _evaluate_activity, we don't need to mock query count unless vote() calls it.
        # vote() calls _evaluate_activity at the end.

        res = service.vote("T1", "Approve", user_id=10)
        assert res is True
        assert task.assigned_to_user_id == 10  # Claimed by 10
        service._evaluate_activity.assert_called_once()

    def test_vote_role_assignment_denied(self, mock_session):
        service = WorkflowService(mock_session)
        task = WorkflowTask(id="T1", status="Pending", assigned_to_role_id=5)
        # User has Role 3 only
        user = RBACUser(id=20, roles=[RBACRole(id=3)])

        def get_side_effect(model, id):
            if model == WorkflowTask:
                return task
            if model == RBACUser:
                return user
            return None

        mock_session.get.side_effect = get_side_effect

        with pytest.raises(ValueError, match="User does not have required role"):
            service.vote("T1", "Approve", user_id=20)
