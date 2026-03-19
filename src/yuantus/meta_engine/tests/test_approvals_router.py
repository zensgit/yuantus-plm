"""Tests for C12 – Generic approvals router."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.database import get_db
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.meta_engine.web.approvals_router import approvals_router


def _client_with_db():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(approvals_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = lambda: None
    return TestClient(app), mock_db_session


def test_category_crud():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.create_category.return_value = SimpleNamespace(
            id="cat-1", name="ECO", parent_id=None, description=None, created_at=None,
        )
        service.list_categories.return_value = [service.create_category.return_value]

        create_resp = client.post("/api/v1/approvals/categories", json={"name": "ECO"})
        list_resp = client.get("/api/v1/approvals/categories")

    assert create_resp.status_code == 200
    assert create_resp.json()["id"] == "cat-1"
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1


def test_request_create_and_list():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.create_request.return_value = SimpleNamespace(
            id="ar-1", title="Approve ECO", category_id="cat-1",
            entity_type="eco", entity_id="eco-1", state="draft",
            priority="high", description="Review BOM changes",
            rejection_reason=None, requested_by_id=None,
            assigned_to_id=None, decided_by_id=None,
            created_at=None, submitted_at=None, decided_at=None, cancelled_at=None,
        )
        service.list_requests.return_value = [service.create_request.return_value]

        create_resp = client.post(
            "/api/v1/approvals/requests",
            json={"title": "Approve ECO", "entity_type": "eco", "priority": "high"},
        )
        list_resp = client.get("/api/v1/approvals/requests")

    assert create_resp.status_code == 200
    assert create_resp.json()["state"] == "draft"
    assert list_resp.json()["total"] == 1


def test_request_transition():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.transition_request.return_value = SimpleNamespace(
            id="ar-1", title="Approve ECO", category_id=None,
            entity_type="eco", entity_id="eco-1", state="pending",
            priority="normal", description=None, rejection_reason=None,
            requested_by_id=None, assigned_to_id=None, decided_by_id=None,
            created_at=None, submitted_at=None, decided_at=None, cancelled_at=None,
        )

        resp = client.post(
            "/api/v1/approvals/requests/ar-1/transition",
            json={"target_state": "pending"},
        )

    assert resp.status_code == 200
    assert resp.json()["state"] == "pending"


def test_request_get():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_request.return_value = SimpleNamespace(
            id="ar-1", title="My Request", category_id=None,
            entity_type=None, entity_id=None, state="draft",
            priority="normal", description=None, rejection_reason=None,
            requested_by_id=None, assigned_to_id=None, decided_by_id=None,
            created_at=None, submitted_at=None, decided_at=None, cancelled_at=None,
        )

        resp = client.get("/api/v1/approvals/requests/ar-1")

    assert resp.status_code == 200
    assert resp.json()["title"] == "My Request"


def test_request_get_404():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_request.return_value = None

        resp = client.get("/api/v1/approvals/requests/no-such")

    assert resp.status_code == 404


def test_summary_endpoint():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_summary.return_value = {
            "total": 5,
            "pending": 2,
            "by_state": {"draft": 1, "pending": 2, "approved": 2},
            "by_priority": {"normal": 3, "high": 2},
            "filters": {"entity_type": "eco", "category_id": None},
        }

        resp = client.get(
            "/api/v1/approvals/summary",
            params={"entity_type": "eco"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["pending"] == 2
    service.get_summary.assert_called_once_with(
        entity_type="eco", category_id=None,
    )


def test_transition_validation_error():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.transition_request.side_effect = ValueError("Cannot transition")

        resp = client.post(
            "/api/v1/approvals/requests/ar-1/transition",
            json={"target_state": "approved"},
        )

    assert resp.status_code == 400
    assert "Cannot transition" in resp.json()["detail"]


def test_approvals_routes_registered_in_create_app():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/v1/approvals/categories" in paths
    assert "/api/v1/approvals/requests" in paths
    assert "/api/v1/approvals/requests/{request_id}" in paths
    assert "/api/v1/approvals/summary" in paths
