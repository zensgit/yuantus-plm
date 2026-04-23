from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.eco import ApprovalStatus
from yuantus.meta_engine.services.eco_service import ECOApprovalService
from yuantus.security.rbac.models import RBACUser, RBACRole


import pytest


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


class _MockQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter_by(self, **kwargs):
        self._items = [
            item
            for item in self._items
            if all(getattr(item, key, None) == value for key, value in kwargs.items())
        ]
        return self

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None

    def count(self):
        return len(self._items)


def _mock_session(*, eco, stage, approvals=None, users=None):
    session = MagicMock()
    approvals = approvals or []
    users = users or []

    def mock_get(model, obj_id):
        if getattr(model, "__name__", "") == "ECO" and obj_id == eco.id:
            return eco
        if getattr(model, "__name__", "") == "ECOStage" and obj_id == stage.id:
            return stage
        return None

    def mock_query(model):
        if model.__name__ == "ECOApproval":
            return _MockQuery(approvals)
        if model.__name__ == "RBACUser":
            return _MockQuery(users)
        raise AssertionError(f"Unexpected query model: {model}")

    session.get.side_effect = mock_get
    session.query.side_effect = mock_query
    return session


def _role(name: str, *, active: bool = True):
    return SimpleNamespace(name=name, is_active=active)


def _user(user_id: int, username: str, roles):
    return SimpleNamespace(
        id=user_id,
        username=username,
        email=f"{username}@example.com",
        roles=list(roles),
        is_active=True,
        is_superuser=False,
    )


def _client_with_user_id(user_id: int):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_user_id():
        return user_id

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_get_user_id
    return TestClient(app), mock_db_session


def test_get_approval_routing_resolves_role_candidates_and_progress():
    eco = SimpleNamespace(
        id="eco-1",
        state="progress",
        stage_id="stage-1",
        approval_deadline=datetime.utcnow() + timedelta(hours=4),
    )
    stage = SimpleNamespace(
        id="stage-1",
        name="QA Review",
        approval_type="mandatory",
        approval_roles=["qa", "mgr"],
        min_approvals=2,
    )
    approvals = [
        SimpleNamespace(
            id="ap-1",
            eco_id="eco-1",
            stage_id="stage-1",
            user_id=1,
            status=ApprovalStatus.APPROVED.value,
            approval_type="mandatory",
            required_role=None,
            comment="ok",
            approved_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ),
        SimpleNamespace(
            id="ap-2",
            eco_id="eco-1",
            stage_id="stage-1",
            user_id=3,
            status=ApprovalStatus.PENDING.value,
            approval_type="mandatory",
            required_role=None,
            comment=None,
            approved_at=None,
            created_at=datetime.utcnow(),
        ),
    ]
    users = [
        _user(1, "alice", [_role("qa")]),
        _user(2, "bob", [_role("engineering")]),
        _user(3, "carol", [_role("mgr"), _role("qa")]),
    ]
    session = _mock_session(eco=eco, stage=stage, approvals=approvals, users=users)
    service = ECOApprovalService(session)
    service.check_stage_approvals_complete = MagicMock(return_value=False)

    routing = service.get_approval_routing("eco-1")

    assert routing["routing_mode"] == "role_based"
    assert routing["routing_ready"] is True
    assert routing["candidate_approver_count"] == 2
    assert routing["approved_count"] == 1
    assert routing["remaining_required"] == 1
    assert routing["stage_complete"] is False
    assert [row["username"] for row in routing["candidate_approvers"]] == ["alice", "carol"]
    assert routing["candidate_approvers"][0]["decision_status"] == "approved"
    assert routing["candidate_approvers"][1]["decision_status"] == "pending"


def test_get_approval_routing_reports_open_gap_when_roles_missing():
    eco = SimpleNamespace(
        id="eco-2",
        state="progress",
        stage_id="stage-2",
        approval_deadline=None,
    )
    stage = SimpleNamespace(
        id="stage-2",
        name="Open Review",
        approval_type="mandatory",
        approval_roles=None,
        min_approvals=1,
    )
    session = _mock_session(eco=eco, stage=stage, approvals=[], users=[])
    service = ECOApprovalService(session)
    service.check_stage_approvals_complete = MagicMock(return_value=False)

    routing = service.get_approval_routing("eco-2")

    assert routing["routing_mode"] == "open"
    assert routing["routing_ready"] is False
    assert "not configured" in routing["routing_gap"]
    assert routing["candidate_approver_count"] == 0


def test_approval_routing_endpoint_returns_service_payload():
    client, _db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as service_cls:
        service = service_cls.return_value
        service.get_approval_routing.return_value = {
            "eco_id": "eco-1",
            "stage_id": "stage-1",
            "routing_mode": "role_based",
            "routing_ready": True,
            "candidate_approver_count": 2,
            "candidate_approvers": [
                {"user_id": 1, "username": "alice", "decision_status": "pending"}
            ],
            "approvals": [],
            "approved_count": 0,
            "rejected_count": 0,
            "remaining_required": 1,
            "stage_complete": False,
        }

        resp = client.get("/api/v1/eco/eco-1/approval-routing")

    assert resp.status_code == 200
    body = resp.json()
    assert body["routing_mode"] == "role_based"
    assert body["candidate_approver_count"] == 2
    service.permission_service.check_permission.assert_called_once_with(
        7, "read", "ECO", resource_id="eco-1"
    )
    service.get_approval_routing.assert_called_once_with("eco-1")


def test_approval_routing_endpoint_maps_missing_eco_to_404():
    client, _db = _client_with_user_id(7)

    with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as service_cls:
        service = service_cls.return_value
        service.get_approval_routing.side_effect = ValueError("ECO not found")

        resp = client.get("/api/v1/eco/no-such/approval-routing")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "ECO not found"
