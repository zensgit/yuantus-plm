from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import get_db


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client():
    app = create_app()
    db = MagicMock()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), db


def test_pending_approvals_returns_service_payload() -> None:
    client, _db = _client()
    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls:
        service_cls.return_value.get_pending_approvals.return_value = [{"eco_id": "eco-1"}]
        resp = client.get("/api/v1/eco/approvals/pending")

    assert resp.status_code == 200
    assert resp.json() == [{"eco_id": "eco-1"}]


def test_batch_approvals_rejects_invalid_mode_before_service_call() -> None:
    client, _db = _client()
    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls:
        resp = client.post(
            "/api/v1/eco/approvals/batch",
            json={"eco_ids": ["eco-1"], "mode": "maybe"},
        )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "mode must be approve|reject"
    service_cls.assert_not_called()


def test_batch_reject_requires_comment() -> None:
    client, _db = _client()
    resp = client.post(
        "/api/v1/eco/approvals/batch",
        json={"eco_ids": ["eco-1"], "mode": "reject"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "comment required for reject"


def test_batch_approve_aggregates_results_and_notifies() -> None:
    client, db = _client()
    approved = MagicMock(id="appr-1", status="approved")
    failed = RuntimeError("boom")

    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls, patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.AuditService"
    ) as audit_cls, patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.NotificationService"
    ) as notify_cls:
        service = service_cls.return_value
        service.approve.side_effect = [approved, failed]
        resp = client.post(
            "/api/v1/eco/approvals/batch",
            json={"eco_ids": ["eco-1", "eco-2"], "mode": "approve"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == {"ok": 1, "failed": 1}
    assert body["results"][0]["approval_id"] == "appr-1"
    assert body["results"][1]["error"] == "boom"
    assert db.commit.call_count == 1
    assert db.rollback.call_count == 1
    audit_cls.return_value.log_action.assert_called_once()
    notify_cls.return_value.notify.assert_called_once()


def test_overdue_approvals_returns_service_payload() -> None:
    client, _db = _client()
    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls:
        service_cls.return_value.list_overdue_approvals.return_value = [{"eco_id": "eco-1"}]
        resp = client.get("/api/v1/eco/approvals/overdue")

    assert resp.status_code == 200
    assert resp.json() == [{"eco_id": "eco-1"}]


def test_notify_overdue_returns_service_payload() -> None:
    client, _db = _client()
    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls:
        service_cls.return_value.notify_overdue_approvals.return_value = {
            "sent": 2,
            "items": ["eco-1", "eco-2"],
        }
        resp = client.post("/api/v1/eco/approvals/notify-overdue")

    assert resp.status_code == 200
    assert resp.json()["sent"] == 2


def test_approve_route_returns_approval_dict() -> None:
    client, db = _client()
    approval = MagicMock()
    approval.to_dict.return_value = {"id": "appr-1", "status": "approved"}

    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls:
        service_cls.return_value.approve.return_value = approval
        resp = client.post("/api/v1/eco/eco-1/approve", json={"comment": "ok"})

    assert resp.status_code == 200
    assert resp.json() == {"id": "appr-1", "status": "approved"}
    db.commit.assert_called_once()


def test_reject_route_returns_approval_dict() -> None:
    client, db = _client()
    approval = MagicMock()
    approval.to_dict.return_value = {"id": "appr-1", "status": "rejected"}

    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls:
        service_cls.return_value.reject.return_value = approval
        resp = client.post("/api/v1/eco/eco-1/reject", json={"comment": "no"})

    assert resp.status_code == 200
    assert resp.json() == {"id": "appr-1", "status": "rejected"}
    db.commit.assert_called_once()


def test_get_eco_approvals_returns_serialized_list() -> None:
    client, _db = _client()
    approval = MagicMock()
    approval.to_dict.return_value = {"id": "appr-1", "status": "pending"}

    with patch(
        "yuantus.meta_engine.web.eco_approval_workflow_router.ECOApprovalService"
    ) as service_cls:
        service_cls.return_value.get_eco_approvals.return_value = [approval]
        resp = client.get("/api/v1/eco/eco-1/approvals")

    assert resp.status_code == 200
    assert resp.json() == [{"id": "appr-1", "status": "pending"}]
