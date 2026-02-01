from sqlalchemy.orm import Session
from yuantus.meta_engine.workflow.service import WorkflowService
from yuantus.meta_engine.workflow.models import (
    WorkflowTask,
    WorkflowActivityInstance,
    WorkflowProcess,
    WorkflowActivity,
)
from yuantus.meta_engine.models.item import Item
from yuantus.security.rbac.models import RBACUser, RBACRole
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestWorkflowInbox:
    @pytest.fixture
    def session(self):
        return MagicMock(spec=Session)

    def test_get_pending_tasks_manual_mock(self, session):
        # We need to constructing a complex chain of objects to test get_pending_tasks
        # User -> Role
        # Task -> ActivityInstance -> Process -> Item

        user = RBACUser(id=1, username="test_user")
        role = RBACRole(id=10, name="Engineer")
        user.roles = [role]

        item1 = Item(id="item1", item_type_id="Part")
        item2 = Item(id="item2", item_type_id="Document")

        def get_side_effect(model, key):
            if model is RBACUser:
                return user
            if model is Item:
                return {"item1": item1, "item2": item2}.get(key)
            return None

        session.get.side_effect = get_side_effect

        # Mock Query
        mock_query = session.query.return_value
        mock_query.filter.return_value = mock_query  # Chaining

        # Setup Tasks
        task1 = WorkflowTask(id="task1", status="Pending", assigned_to_user_id=1)
        task2 = WorkflowTask(id="task2", status="Pending", assigned_to_role_id=10)

        # Setup Relationships (Mocking deeply nested objects is painful without integration DB)
        # So we just mock the attributes accessed

        # Task 1 Context
        proc1 = WorkflowProcess(id="proc1", item_id="item1", state="Active")
        act1 = WorkflowActivity(name="Review", description="Review 1")
        inst1 = WorkflowActivityInstance(id="inst1", created_at=datetime.utcnow())
        inst1.activity = act1
        inst1.process = proc1
        task1.activity_instance = inst1

        # Task 2 Context
        proc2 = WorkflowProcess(id="proc2", item_id="item2", state="Active")
        act2 = WorkflowActivity(name="Approve", description="Approve 2")
        inst2 = WorkflowActivityInstance(id="inst2", created_at=datetime.utcnow())
        inst2.activity = act2
        inst2.process = proc2
        task2.activity_instance = inst2

        mock_query.all.side_effect = [[task1], [task2]]

        svc = WorkflowService(session)
        tasks = svc.get_pending_tasks(user_id=1)

        assert len(tasks) == 2

        t1_res = next(t for t in tasks if t["id"] == "task1")
        assert t1_res["activity"] == "Review"
        assert t1_res["item"]["id"] == "item1"

        t2_res = next(t for t in tasks if t["id"] == "task2")
        assert t2_res["activity"] == "Approve"
