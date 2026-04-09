"""Tests for C12 – Generic approvals router."""
from __future__ import annotations

from datetime import datetime, timedelta
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
        svc_cls._age_hours.return_value = 5.0
        service.get_request.return_value = SimpleNamespace(
            id="ar-1", title="My Request", category_id=None,
            entity_type=None, entity_id=None, state="draft",
            priority="normal", description=None, rejection_reason=None,
            requested_by_id=None, assigned_to_id=None, decided_by_id=None,
            created_at=datetime.utcnow() - timedelta(hours=5),
            submitted_at=None, decided_at=None, cancelled_at=None,
        )

        resp = client.get("/api/v1/approvals/requests/ar-1")

    assert resp.status_code == 200
    assert resp.json()["title"] == "My Request"
    assert resp.json()["age_hours"] >= 4.9


def test_request_get_404():
    client, db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_request.return_value = None

        resp = client.get("/api/v1/approvals/requests/no-such")

    assert resp.status_code == 404


def test_request_lifecycle_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_request_lifecycle.return_value = {
            "request_id": "ar-1",
            "current_state": "pending",
            "milestone_count": 2,
            "latest": {"event_type": "submitted"},
            "milestones": [{"event_type": "created"}, {"event_type": "submitted"}],
            "generated_at": "2026-03-23T00:00:00Z",
        }

        resp = client.get("/api/v1/approvals/requests/ar-1/lifecycle")

    assert resp.status_code == 200
    assert resp.json()["latest"]["event_type"] == "submitted"
    service.get_request_lifecycle.assert_called_once_with("ar-1")


def test_request_consumer_summary_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_request_consumer_summary.return_value = {
            "request": {"id": "ar-1", "state": "pending"},
            "status": {"requires_decision": True},
            "proof": {
                "assignment": {"assigned_to_id": 8},
                "lifecycle": {"latest": {"event_type": "submitted"}},
                "allowed_transitions": ["approved", "rejected"],
            },
            "generated_at": "2026-03-23T00:00:00Z",
        }

        resp = client.get("/api/v1/approvals/requests/ar-1/consumer-summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"]["requires_decision"] is True
    assert body["proof"]["lifecycle"]["latest"]["event_type"] == "submitted"
    assert body["urls"]["transition"].endswith("/api/v1/approvals/requests/ar-1/transition")
    service.get_request_consumer_summary.assert_called_once_with(
        "ar-1",
        include_history=False,
        history_limit=5,
    )


def test_request_history_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_request_history.return_value = {
            "request_id": "ar-1",
            "total": 2,
            "latest": {"event_type": "transition", "to_state": "pending"},
            "events": [{"event_type": "transition", "to_state": "pending"}],
            "generated_at": "2026-03-23T00:00:00Z",
        }

        resp = client.get("/api/v1/approvals/requests/ar-1/history", params={"history_limit": 3})

    assert resp.status_code == 200
    assert resp.json()["total"] == 2
    assert resp.json()["latest"]["to_state"] == "pending"
    service.get_request_history.assert_called_once_with("ar-1", limit=3)


def test_request_pack_summary_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_request_pack_row.side_effect = [
            {
                "request_id": "ar-1",
                "found": True,
                "title": "Approve ECO",
                "state": "pending",
                "priority": "high",
                "entity_type": "eco",
                "entity_id": "eco-1",
                "assigned_to_id": 8,
                "status": {"is_terminal": False},
                "proof": {"audit": {"enabled": True}},
            },
            {
                "request_id": "missing",
                "found": False,
                "state": "not_found",
                "priority": None,
                "entity_type": None,
                "entity_id": None,
                "assigned_to_id": None,
                "status": None,
                "proof": None,
            },
        ]

        resp = client.post(
            "/api/v1/approvals/requests/pack-summary",
            params={"include_history": "true", "history_limit": 3},
            json={"request_ids": ["ar-1", "missing"]},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["requested_count"] == 2
    assert body["found_count"] == 1
    assert body["not_found_count"] == 1
    assert body["pending_count"] == 1
    assert body["terminal_count"] == 0
    assert body["requests"][0]["proof"]["audit"]["enabled"] is True
    assert service.get_request_pack_row.call_count == 2


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


def test_requests_export_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.export_requests.return_value = {
            "requests": [{"id": "ar-1", "title": "Approve ECO"}],
            "filters": {"entity_type": "eco"},
            "generated_at": "2026-03-19T00:00:00Z",
        }

        resp = client.get(
            "/api/v1/approvals/requests/export",
            params={"format": "JSON", "entity_type": "eco"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-disposition"].endswith('approval-requests-export.json"')
    assert resp.json()["requests"][0]["id"] == "ar-1"
    service.export_requests.assert_called_once_with(
        fmt="json",
        state=None,
        category_id=None,
        entity_type="eco",
        entity_id=None,
        priority=None,
        assigned_to_id=None,
    )


def test_summary_export_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.export_summary.return_value = "metric,value\ntotal,2\n"

        resp = client.get(
            "/api/v1/approvals/summary/export",
            params={"format": "csv"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "metric,value" in resp.text
    service.export_summary.assert_called_once_with(
        fmt="csv",
        entity_type=None,
        category_id=None,
    )


def test_ops_report_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_ops_report.return_value = {
            "category_coverage": 0.5,
            "entity_link_coverage": 1.0,
            "assignment_coverage": 0.25,
            "terminal_state_coverage": 0.75,
            "bootstrap_ready": False,
        }

        resp = client.get("/api/v1/approvals/ops-report")

    assert resp.status_code == 200
    assert resp.json()["bootstrap_ready"] is False
    service.get_ops_report.assert_called_once_with()


def test_ops_report_export_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.export_ops_report.return_value = "# Approvals Ops Report\n"

        resp = client.get(
            "/api/v1/approvals/ops-report/export",
            params={"format": "markdown"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "# Approvals Ops Report" in resp.text
    service.export_ops_report.assert_called_once_with(fmt="markdown")


def test_queue_health_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.get_queue_health.return_value = {
            "generated_at": "2026-03-23T00:00:00Z",
            "filters": {"entity_type": "eco", "category_id": None},
            "thresholds": {"warn_after_hours": 4, "stale_after_hours": 24},
            "total": 2,
            "pending": 1,
            "pending_ratio": 0.5,
            "by_state": {"pending": 1, "approved": 1},
            "by_priority": {"normal": 1, "high": 1},
            "pending_age": {
                "oldest_hours": 30.0,
                "average_hours": 30.0,
                "oldest_request": {"id": "ar-1"},
                "fresh_count": 0,
                "watch_count": 0,
                "stale_count": 1,
            },
            "unassigned_pending_count": 1,
            "risk_flags": ["stale_pending_backlog"],
            "health_status": "degraded",
            "operational_ready": False,
        }

        resp = client.get(
            "/api/v1/approvals/queue-health",
            params={"entity_type": "eco"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["health_status"] == "degraded"
    assert body["pending_age"]["stale_count"] == 1
    service.get_queue_health.assert_called_once_with(
        stale_after_hours=24,
        warn_after_hours=4,
        entity_type="eco",
        category_id=None,
    )


def test_queue_health_export_endpoint():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.approvals_router.ApprovalService") as svc_cls:
        service = svc_cls.return_value
        service.export_queue_health.return_value = "metric,value\npending,1\n"

        resp = client.get(
            "/api/v1/approvals/queue-health/export",
            params={"format": "csv"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "metric,value" in resp.text
    service.export_queue_health.assert_called_once_with(
        fmt="csv",
        stale_after_hours=24,
        warn_after_hours=4,
        entity_type=None,
        category_id=None,
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
    assert "/api/v1/approvals/requests/export" in paths
    assert "/api/v1/approvals/requests/{request_id}/lifecycle" in paths
    assert "/api/v1/approvals/requests/{request_id}/history" in paths
    assert "/api/v1/approvals/requests/{request_id}/consumer-summary" in paths
    assert "/api/v1/approvals/requests/pack-summary" in paths
    assert "/api/v1/approvals/requests/{request_id}" in paths
    assert "/api/v1/approvals/summary" in paths
    assert "/api/v1/approvals/summary/export" in paths
    assert "/api/v1/approvals/ops-report" in paths
    assert "/api/v1/approvals/ops-report/export" in paths
    assert "/api/v1/approvals/queue-health" in paths
    assert "/api/v1/approvals/queue-health/export" in paths
