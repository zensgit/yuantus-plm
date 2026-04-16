"""
P2-3.1 PR-3: Approval Ops Audit — Focused Tests
=================================================
Covers:
  - no_candidates: stage needs approval but 0 eligible users
  - escalated_unresolved: admin-escalated still pending
  - overdue_not_escalated: overdue without admin escalation
  - HTTP route registered + 200
  - total_anomalies = sum of all three
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from yuantus.meta_engine.services.eco_service import ECOApprovalService


def _mock_eco(eco_id, stage_id, state="progress", deadline=None):
    e = MagicMock()
    e.id = eco_id; e.name = f"ECO-{eco_id}"; e.state = state
    e.stage_id = stage_id; e.approval_deadline = deadline; e.company_id = None
    return e


def _mock_stage(stage_id, name, approval_type="mandatory", roles=None):
    s = MagicMock()
    s.id = stage_id; s.name = name
    s.approval_type = approval_type
    s.approval_roles = roles or ["engineer"]
    return s


def _svc(session):
    svc = ECOApprovalService(session)
    svc.notification_service = MagicMock()
    svc.audit_service = MagicMock()
    return svc


class TestNoCandidates:
    def test_detected_when_no_active_users_match(self):
        session = MagicMock()
        eco = _mock_eco("e1", "s1")
        stage = _mock_stage("s1", "Review", roles=["specialist"])

        session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            (eco, stage)
        ]
        # _resolve_candidate_users returns empty
        session.query.return_value.filter.return_value.all.return_value = []

        svc = _svc(session)
        # Mock away the other two queries
        svc.list_overdue_approvals = MagicMock(return_value=[])
        result = svc.get_approval_anomalies()

        assert len(result["no_candidates"]) == 1
        assert result["no_candidates"][0]["eco_id"] == "e1"
        assert "specialist" in str(result["no_candidates"][0]["approval_roles"])

    def test_not_flagged_when_candidates_exist(self):
        session = MagicMock()
        eco = _mock_eco("e1", "s1")
        stage = _mock_stage("s1", "Review", roles=["engineer"])
        user = MagicMock(id=10, username="alice", is_superuser=False, is_active=True)
        role = MagicMock(name="engineer", is_active=True)
        user.roles = [role]

        # ecos_with_stages
        first_q = MagicMock()
        first_q.join.return_value.filter.return_value.all.return_value = [(eco, stage)]
        # esc_rows
        second_q = MagicMock()
        second_q.join.return_value.join.return_value.filter.return_value.all.return_value = []

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return first_q
            if call_count[0] == 2:
                return second_q
            return MagicMock()
        session.query.side_effect = query_side

        svc = _svc(session)
        svc._resolve_candidate_users = MagicMock(return_value=[user])
        svc.list_overdue_approvals = MagicMock(return_value=[])
        result = svc.get_approval_anomalies()

        assert len(result["no_candidates"]) == 0


class TestEscalatedUnresolved:
    def test_detected_when_admin_pending(self):
        session = MagicMock()
        appr = MagicMock(
            id="a1", eco_id="e1", stage_id="s1", user_id=99,
            required_role="admin", status="pending",
        )
        eco = _mock_eco("e1", "s1")
        stage = _mock_stage("s1", "Review")
        admin = MagicMock(username="admin-user")

        # ecos_with_stages → empty (no candidates to check)
        first_query = MagicMock()
        first_query.join.return_value.filter.return_value.all.return_value = []
        # esc_rows query
        second_query = MagicMock()
        second_query.join.return_value.join.return_value.filter.return_value.all.return_value = [
            (appr, eco, stage)
        ]

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return first_query
            if call_count[0] == 2:
                return second_query
            return MagicMock()
        session.query.side_effect = query_side
        session.get.return_value = admin

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[])
        result = svc.get_approval_anomalies()

        assert len(result["escalated_unresolved"]) == 1
        assert result["escalated_unresolved"][0]["admin_user_id"] == 99

    def test_old_stage_admin_pending_excluded(self):
        """ECO moved to stage s2, but old stage s1 still has admin pending.
        Anomaly report must NOT include the old stage record."""
        import inspect
        src = inspect.getsource(ECOApprovalService.get_approval_anomalies)
        # The query must bind approval stage to ECO's current stage
        assert "ECOApproval.stage_id == ECO.stage_id" in src


class TestOverdueNotEscalated:
    def test_detected_when_overdue_and_no_admin_approval(self):
        session = MagicMock()
        # ecos_with_stages → empty
        session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        session.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []
        # No admin approval exists
        session.query.return_value.filter_by.return_value.first.return_value = None

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[{
            "eco_id": "e2", "eco_name": "ECO-2",
            "stage_id": "s1", "stage_name": "Review",
            "hours_overdue": 8.0,
        }])
        result = svc.get_approval_anomalies()

        assert len(result["overdue_not_escalated"]) == 1
        assert result["overdue_not_escalated"][0]["hours_overdue"] == 8.0

    def test_not_flagged_when_admin_exists(self):
        session = MagicMock()
        session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        session.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []
        # Admin approval EXISTS
        session.query.return_value.filter_by.return_value.first.return_value = MagicMock()

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[{
            "eco_id": "e2", "eco_name": "ECO-2",
            "stage_id": "s1", "stage_name": "Review",
            "hours_overdue": 3.0,
        }])
        result = svc.get_approval_anomalies()

        assert len(result["overdue_not_escalated"]) == 0


class TestTotalAnomalies:
    def test_total_is_sum(self):
        session = MagicMock()
        session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        session.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter_by.return_value.first.return_value = None

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[
            {"eco_id": "e1", "eco_name": "E1", "stage_id": "s1", "stage_name": "R", "hours_overdue": 1},
            {"eco_id": "e2", "eco_name": "E2", "stage_id": "s2", "stage_name": "R", "hours_overdue": 2},
        ])
        result = svc.get_approval_anomalies()

        expected = (
            len(result["no_candidates"])
            + len(result["escalated_unresolved"])
            + len(result["overdue_not_escalated"])
        )
        assert result["total_anomalies"] == expected


class TestAuditHTTP:
    def _client(self):
        from fastapi.testclient import TestClient
        from yuantus.api.app import create_app
        from yuantus.database import get_db
        app = create_app()
        db = MagicMock()
        def override():
            try: yield db
            finally: pass
        app.dependency_overrides[get_db] = override
        return TestClient(app), db

    def test_route_registered(self):
        from yuantus.api.app import create_app
        app = create_app()
        paths = {r.path for r in app.routes}
        assert "/api/v1/eco/approvals/audit/anomalies" in paths

    def test_returns_200_with_shape(self):
        client, db = self._client()
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.get_approval_anomalies.return_value = {
                "no_candidates": [], "escalated_unresolved": [],
                "overdue_not_escalated": [], "total_anomalies": 0,
            }
            resp = client.get("/api/v1/eco/approvals/audit/anomalies")
        assert resp.status_code == 200
        body = resp.json()
        assert "no_candidates" in body
        assert "escalated_unresolved" in body
        assert "overdue_not_escalated" in body
        assert body["total_anomalies"] == 0
