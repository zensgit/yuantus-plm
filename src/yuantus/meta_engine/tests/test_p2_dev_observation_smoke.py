"""
P2 Dev Observation Startup — Smoke Tests
==========================================
Checklist items 7-11: verify all 6 P2 endpoints are reachable
and return correct shapes via TestClient (no real DB/server needed).
"""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.database import get_db


def _client():
    app = create_app()
    db = MagicMock()
    def override():
        try: yield db
        finally: pass
    app.dependency_overrides[get_db] = override
    return TestClient(app), db


# ========================================================================
# Checklist #3: All 6 P2 endpoints reachable
# ========================================================================

class TestEndpointReachability:
    def test_dashboard_summary_reachable(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_summary.return_value = {
                "pending_count": 0, "overdue_count": 0, "escalated_count": 0,
                "by_stage": [], "by_role": [], "by_assignee": [],
            }
            resp = client.get("/api/v1/eco/approvals/dashboard/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert "pending_count" in body
        assert "overdue_count" in body
        assert "escalated_count" in body

    def test_dashboard_items_reachable(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_items.return_value = []
            resp = client.get("/api/v1/eco/approvals/dashboard/items")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_dashboard_export_json_reachable(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.export_dashboard_items.return_value = "[]"
            resp = client.get("/api/v1/eco/approvals/dashboard/export?fmt=json")
        assert resp.status_code == 200

    def test_dashboard_export_csv_reachable(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.export_dashboard_items.return_value = "eco_id\n"
            resp = client.get("/api/v1/eco/approvals/dashboard/export?fmt=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_audit_anomalies_reachable(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_anomalies.return_value = {
                "no_candidates": [], "escalated_unresolved": [],
                "overdue_not_escalated": [], "total_anomalies": 0,
            }
            resp = client.get("/api/v1/eco/approvals/audit/anomalies")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_anomalies"] == 0

    def test_auto_assign_reachable_returns_400_for_missing_eco(self):
        """auto-assign needs auth — mock service to raise ValueError."""
        client, _ = _client()
        from yuantus.api.dependencies.auth import get_current_user_id
        app = client.app
        app.dependency_overrides[get_current_user_id] = lambda: 1
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.auto_assign_stage_approvers.side_effect = ValueError("ECO not found")
            resp = client.post("/api/v1/eco/eco-test/auto-assign-approvers")
        assert resp.status_code == 400

    def test_escalate_overdue_reachable(self):
        client, _ = _client()
        from yuantus.api.dependencies.auth import get_current_user_id
        app = client.app
        app.dependency_overrides[get_current_user_id] = lambda: 1
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.escalate_overdue_approvals.return_value = {
                "escalated": 0, "items": [],
            }
            resp = client.post("/api/v1/eco/approvals/escalate-overdue")
        assert resp.status_code == 200
        assert resp.json()["escalated"] == 0


# ========================================================================
# Checklist #10: Baseline observation — empty state behavior
# ========================================================================

class TestEmptyStateBaseline:
    """Verify correct behavior when no ECO data exists."""

    def test_summary_all_zeros(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_summary.return_value = {
                "pending_count": 0, "overdue_count": 0, "escalated_count": 0,
                "by_stage": [], "by_role": [], "by_assignee": [],
            }
            resp = client.get("/api/v1/eco/approvals/dashboard/summary")
        body = resp.json()
        assert body["pending_count"] == 0
        assert body["overdue_count"] == 0
        assert body["escalated_count"] == 0
        assert body["by_stage"] == []
        assert body["by_assignee"] == []

    def test_anomalies_all_empty(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_anomalies.return_value = {
                "no_candidates": [], "escalated_unresolved": [],
                "overdue_not_escalated": [], "total_anomalies": 0,
            }
            resp = client.get("/api/v1/eco/approvals/audit/anomalies")
        body = resp.json()
        assert body["total_anomalies"] == 0

    def test_export_csv_empty_has_header_only(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            # CSV with header only
            M.return_value.export_dashboard_items.return_value = (
                "eco_id,eco_name,eco_state,stage_id,stage_name,"
                "approval_id,assignee_id,assignee_username,"
                "approval_type,required_role,is_overdue,is_escalated,"
                "approval_deadline,hours_overdue\r\n"
            )
            resp = client.get("/api/v1/eco/approvals/dashboard/export?fmt=csv")
        lines = resp.text.strip().split("\n")
        assert len(lines) == 1  # header only
        assert "eco_id" in lines[0]


# ========================================================================
# Checklist #11: Filter params work
# ========================================================================

class TestFilterParams:
    def test_summary_accepts_all_filters(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_summary.return_value = {
                "pending_count": 0, "overdue_count": 0, "escalated_count": 0,
                "by_stage": [], "by_role": [], "by_assignee": [],
            }
            resp = client.get(
                "/api/v1/eco/approvals/dashboard/summary"
                "?company_id=acme&eco_type=bom&eco_state=progress"
                "&deadline_from=2026-04-01T00:00:00&deadline_to=2026-04-30T23:59:59"
            )
        assert resp.status_code == 200

    def test_items_accepts_status_filter(self):
        client, _ = _client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_items.return_value = []
            resp = client.get(
                "/api/v1/eco/approvals/dashboard/items?status=overdue&limit=5"
            )
        assert resp.status_code == 200

    def test_bad_deadline_returns_400(self):
        client, _ = _client()
        resp = client.get(
            "/api/v1/eco/approvals/dashboard/summary?deadline_from=garbage"
        )
        assert resp.status_code == 400
