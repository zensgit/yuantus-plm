"""
P2-3: ECO Approval SLA Dashboard — Focused Tests
==================================================
Covers:
  - summary endpoint: overdue/pending/escalated counts, by_stage, by_role, by_assignee
  - items endpoint: overdue/pending/escalated filters, stage/assignee/role filters
  - API contract: routes registered, response shape
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from yuantus.config import get_settings
from yuantus.meta_engine.services.eco_service import ECOApprovalService


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _mock_eco(eco_id, stage_id, deadline=None, state="progress"):
    e = MagicMock()
    e.id = eco_id; e.name = f"ECO-{eco_id}"; e.state = state
    e.stage_id = stage_id; e.approval_deadline = deadline
    return e


def _mock_stage(stage_id, name, approval_type="mandatory", roles=None):
    s = MagicMock()
    s.id = stage_id; s.name = name
    s.approval_type = approval_type
    s.approval_roles = roles or ["engineer"]
    return s


def _mock_approval(appr_id, eco_id, stage_id, user_id, status="pending", required_role=None):
    a = MagicMock()
    a.id = appr_id; a.eco_id = eco_id; a.stage_id = stage_id
    a.user_id = user_id; a.status = status
    a.approval_type = "mandatory"; a.required_role = required_role
    return a


def _svc(session):
    svc = ECOApprovalService(session)
    svc.notification_service = MagicMock()
    svc.audit_service = MagicMock()
    return svc


# ========================================================================
# API contract
# ========================================================================

class TestDashboardRoutes:
    def test_summary_route_registered(self):
        from yuantus.api.app import create_app
        app = create_app()
        paths = {r.path for r in app.routes}
        assert "/api/v1/eco/approvals/dashboard/summary" in paths

    def test_items_route_registered(self):
        from yuantus.api.app import create_app
        app = create_app()
        paths = {r.path for r in app.routes}
        assert "/api/v1/eco/approvals/dashboard/items" in paths


# ========================================================================
# Summary
# ========================================================================

class TestDashboardSummary:
    def test_returns_all_required_keys(self):
        session = MagicMock()
        # No active ECOs
        session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        # escalated count
        session.query.return_value.filter.return_value.count.return_value = 0
        # by_assignee
        session.query.return_value.filter.return_value.group_by.return_value.all.return_value = []

        svc = _svc(session)
        result = svc.get_approval_dashboard_summary()

        assert "pending_count" in result
        assert "overdue_count" in result
        assert "escalated_count" in result
        assert "by_stage" in result
        assert "by_role" in result
        assert "by_assignee" in result

    def test_counts_overdue_vs_pending(self):
        session = MagicMock()
        now = datetime.utcnow()
        eco_overdue = _mock_eco("e1", "s1", deadline=now - timedelta(hours=5))
        eco_pending = _mock_eco("e2", "s1", deadline=now + timedelta(hours=5))
        stage = _mock_stage("s1", "Review", roles=["engineer"])
        appr1 = _mock_approval("a1", "e1", "s1", 10)
        appr2 = _mock_approval("a2", "e2", "s1", 11)

        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = [
            (eco_overdue, stage, appr1), (eco_pending, stage, appr2),
        ]
        session.get.return_value = MagicMock(username="user")

        result = svc.get_approval_dashboard_summary()
        assert result["overdue_count"] == 1
        assert result["pending_count"] == 1

    def test_by_stage_aggregation(self):
        session = MagicMock()
        now = datetime.utcnow()
        eco1 = _mock_eco("e1", "s1", deadline=now + timedelta(hours=1))
        eco2 = _mock_eco("e2", "s2", deadline=now + timedelta(hours=1))
        stage1 = _mock_stage("s1", "Review")
        stage2 = _mock_stage("s2", "Final")
        appr1 = _mock_approval("a1", "e1", "s1", 10)
        appr2 = _mock_approval("a2", "e2", "s2", 11)

        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = [
            (eco1, stage1, appr1), (eco2, stage2, appr2),
        ]
        session.get.return_value = MagicMock(username="user")

        result = svc.get_approval_dashboard_summary()
        stage_ids = [s["stage_id"] for s in result["by_stage"]]
        assert "s1" in stage_ids
        assert "s2" in stage_ids

    def test_by_role_aggregation(self):
        session = MagicMock()
        now = datetime.utcnow()
        eco = _mock_eco("e1", "s1", deadline=now + timedelta(hours=1))
        stage = _mock_stage("s1", "Review", roles=["engineer", "qa"])
        appr = _mock_approval("a1", "e1", "s1", 10)

        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = [(eco, stage, appr)]
        session.get.return_value = MagicMock(username="user")

        result = svc.get_approval_dashboard_summary()
        role_names = [r["role"] for r in result["by_role"]]
        assert "engineer" in role_names
        assert "qa" in role_names

    def test_excludes_none_approval_stages(self):
        """Base query filters approval_type != none, so empty rows → zeros."""
        session = MagicMock()
        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = []

        result = svc.get_approval_dashboard_summary()
        assert result["pending_count"] == 0
        assert result["overdue_count"] == 0


# ========================================================================
# Items
# ========================================================================

class TestDashboardItems:
    def test_returns_item_shape(self):
        session = MagicMock()
        now = datetime.utcnow()
        eco = _mock_eco("e1", "s1", deadline=now + timedelta(hours=1))
        stage = _mock_stage("s1", "Review")
        appr = _mock_approval("a1", "e1", "s1", 10)
        user = MagicMock(username="alice")

        session.query.return_value.join.return_value.join.return_value.filter.return_value \
            .order_by.return_value.limit.return_value.all.return_value = [(eco, stage, appr)]
        session.get.return_value = user

        svc = _svc(session)
        items = svc.get_approval_dashboard_items()

        assert len(items) == 1
        item = items[0]
        assert item["eco_id"] == "e1"
        assert item["stage_id"] == "s1"
        assert item["assignee_id"] == 10
        assert item["assignee_username"] == "alice"
        assert "is_overdue" in item
        assert "is_escalated" in item

    def test_overdue_filter(self):
        """status=overdue should add deadline filter."""
        import inspect
        src = inspect.getsource(ECOApprovalService.get_approval_dashboard_items)
        assert 'status_filter == "overdue"' in src
        assert "approval_deadline" in src

    def test_escalated_filter(self):
        """status=escalated should filter required_role=admin."""
        import inspect
        src = inspect.getsource(ECOApprovalService.get_approval_dashboard_items)
        assert 'status_filter == "escalated"' in src
        assert 'required_role == "admin"' in src


# ========================================================================
# HTTP integration
# ========================================================================

class TestDashboardHTTP:
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

    def test_summary_200(self):
        client, db = self._client()
        with patch("yuantus.meta_engine.web.eco_approval_ops_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_summary.return_value = {
                "pending_count": 3, "overdue_count": 1, "escalated_count": 0,
                "by_stage": [], "by_role": [], "by_assignee": [],
            }
            resp = client.get("/api/v1/eco/approvals/dashboard/summary")
        assert resp.status_code == 200
        assert resp.json()["pending_count"] == 3

    def test_items_200_with_filter(self):
        client, db = self._client()
        with patch("yuantus.meta_engine.web.eco_approval_ops_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_items.return_value = []
            resp = client.get("/api/v1/eco/approvals/dashboard/items?status=overdue&limit=10")
        assert resp.status_code == 200
        M.return_value.get_approval_dashboard_items.assert_called_once()


# ========================================================================
# R2 fixes: current-stage binding + unified statistics
# ========================================================================

class TestCurrentStageBinding:
    """Items and summary must only include approvals for ECO's current stage."""

    def test_base_query_joins_approval_stage_to_eco_stage(self):
        """_base_dashboard_query must join ECOApproval.stage_id == ECO.stage_id."""
        import inspect
        src = inspect.getsource(ECOApprovalService._base_dashboard_query)
        assert "ECOApproval.stage_id == ECO.stage_id" in src

    def test_summary_and_items_share_base_query(self):
        """Both methods must call _base_dashboard_query for consistent stats."""
        import inspect
        summary_src = inspect.getsource(ECOApprovalService.get_approval_dashboard_summary)
        items_src = inspect.getsource(ECOApprovalService.get_approval_dashboard_items)
        assert "_base_dashboard_query" in summary_src
        assert "_base_dashboard_query" in items_src


class TestUnifiedStatistics:
    """Summary headline numbers must be derivable from items."""

    def test_summary_counts_match_row_count(self):
        """pending_count + overdue_count == total rows from base query."""
        session = MagicMock()
        now = datetime.utcnow()

        eco1 = _mock_eco("e1", "s1", deadline=now - timedelta(hours=2))  # overdue
        eco2 = _mock_eco("e2", "s1", deadline=now + timedelta(hours=2))  # pending
        stage = _mock_stage("s1", "Review", roles=["engineer"])
        appr1 = _mock_approval("a1", "e1", "s1", 10)
        appr2 = _mock_approval("a2", "e2", "s1", 11)
        appr3 = _mock_approval("a3", "e2", "s1", 12)  # 2 approvers for eco2

        rows = [(eco1, stage, appr1), (eco2, stage, appr2), (eco2, stage, appr3)]

        svc = _svc(session)
        # Patch _base_dashboard_query to return our controlled rows
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = rows
        session.get.return_value = MagicMock(username="user")

        result = svc.get_approval_dashboard_summary()

        total = result["pending_count"] + result["overdue_count"]
        assert total == 3  # matches row count, not ECO count
        assert result["overdue_count"] == 1
        assert result["pending_count"] == 2

    def test_by_assignee_sums_to_total(self):
        """Sum of by_assignee.pending_count == pending_count + overdue_count."""
        session = MagicMock()
        now = datetime.utcnow()
        eco = _mock_eco("e1", "s1", deadline=now + timedelta(hours=1))
        stage = _mock_stage("s1", "Review")
        appr1 = _mock_approval("a1", "e1", "s1", 10)
        appr2 = _mock_approval("a2", "e1", "s1", 11)

        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = [
            (eco, stage, appr1), (eco, stage, appr2)
        ]
        session.get.return_value = MagicMock(username="user")

        result = svc.get_approval_dashboard_summary()

        total = result["pending_count"] + result["overdue_count"]
        assignee_sum = sum(a["pending_count"] for a in result["by_assignee"])
        assert assignee_sum == total

    def test_escalated_count_subset_of_total(self):
        """escalated_count must be <= total rows."""
        session = MagicMock()
        now = datetime.utcnow()
        eco = _mock_eco("e1", "s1", deadline=now - timedelta(hours=1))
        stage = _mock_stage("s1", "Review")
        appr_normal = _mock_approval("a1", "e1", "s1", 10)
        appr_admin = _mock_approval("a2", "e1", "s1", 99, required_role="admin")

        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = [
            (eco, stage, appr_normal), (eco, stage, appr_admin)
        ]
        session.get.return_value = MagicMock(username="user")

        result = svc.get_approval_dashboard_summary()

        assert result["escalated_count"] == 1
        total = result["pending_count"] + result["overdue_count"]
        assert result["escalated_count"] <= total


# ========================================================================
# P2-3.1 PR-1: New filters
# ========================================================================

class TestDashboardFilters:
    def test_base_query_accepts_company_id(self):
        """_base_dashboard_query must accept company_id kwarg."""
        import inspect
        sig = inspect.signature(ECOApprovalService._base_dashboard_query)
        assert "company_id" in sig.parameters

    def test_base_query_accepts_eco_type(self):
        import inspect
        sig = inspect.signature(ECOApprovalService._base_dashboard_query)
        assert "eco_type" in sig.parameters

    def test_base_query_accepts_eco_state(self):
        import inspect
        sig = inspect.signature(ECOApprovalService._base_dashboard_query)
        assert "eco_state" in sig.parameters

    def test_base_query_accepts_deadline_range(self):
        import inspect
        sig = inspect.signature(ECOApprovalService._base_dashboard_query)
        assert "deadline_from" in sig.parameters
        assert "deadline_to" in sig.parameters

    def test_summary_passes_filters_to_base_query(self):
        """summary must forward all filter kwargs to _base_dashboard_query."""
        session = MagicMock()
        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        svc._base_dashboard_query.return_value.all.return_value = []

        svc.get_approval_dashboard_summary(
            company_id="acme", eco_type="bom", eco_state="progress",
        )

        svc._base_dashboard_query.assert_called_once()
        kw = svc._base_dashboard_query.call_args[1]
        assert kw["company_id"] == "acme"
        assert kw["eco_type"] == "bom"
        assert kw["eco_state"] == "progress"

    def test_items_passes_filters_to_base_query(self):
        """items must forward all filter kwargs to _base_dashboard_query."""
        session = MagicMock()
        svc = _svc(session)
        svc._base_dashboard_query = MagicMock()
        q = svc._base_dashboard_query.return_value
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.all.return_value = []

        svc.get_approval_dashboard_items(
            company_id="acme", eco_type="routing",
        )

        kw = svc._base_dashboard_query.call_args[1]
        assert kw["company_id"] == "acme"
        assert kw["eco_type"] == "routing"

    def test_router_summary_accepts_filter_params(self):
        """HTTP GET /summary must accept company_id, eco_type, eco_state, deadline_from/to."""
        client, db = TestDashboardHTTP()._client()
        with patch("yuantus.meta_engine.web.eco_approval_ops_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_summary.return_value = {
                "pending_count": 0, "overdue_count": 0, "escalated_count": 0,
                "by_stage": [], "by_role": [], "by_assignee": [],
            }
            resp = client.get(
                "/api/v1/eco/approvals/dashboard/summary"
                "?company_id=acme&eco_type=bom&eco_state=progress"
            )
        assert resp.status_code == 200
        kw = M.return_value.get_approval_dashboard_summary.call_args[1]
        assert kw["company_id"] == "acme"
        assert kw["eco_type"] == "bom"
        assert kw["eco_state"] == "progress"

    def test_router_items_accepts_filter_params(self):
        """HTTP GET /items must accept new filter params alongside existing ones."""
        client, db = TestDashboardHTTP()._client()
        with patch("yuantus.meta_engine.web.eco_approval_ops_router.ECOApprovalService") as M:
            M.return_value.get_approval_dashboard_items.return_value = []
            resp = client.get(
                "/api/v1/eco/approvals/dashboard/items"
                "?company_id=acme&eco_type=bom&status=overdue"
            )
        assert resp.status_code == 200
        kw = M.return_value.get_approval_dashboard_items.call_args[1]
        assert kw["company_id"] == "acme"
        assert kw["eco_type"] == "bom"

    def test_summary_filters_consistent_with_items(self):
        """Both endpoints accept the same filter set → consistent scoping."""
        import inspect
        summary_sig = inspect.signature(ECOApprovalService.get_approval_dashboard_summary)
        items_sig = inspect.signature(ECOApprovalService.get_approval_dashboard_items)
        shared_filters = {"company_id", "eco_type", "eco_state", "deadline_from", "deadline_to"}
        for f in shared_filters:
            assert f in summary_sig.parameters, f"{f} missing from summary"
            assert f in items_sig.parameters, f"{f} missing from items"

    def test_invalid_deadline_from_returns_400(self):
        """Bad deadline_from → 400, not 500."""
        client, db = TestDashboardHTTP()._client()
        resp = client.get(
            "/api/v1/eco/approvals/dashboard/summary?deadline_from=not-a-date"
        )
        assert resp.status_code == 400
        assert "deadline_from" in resp.json()["detail"]

    def test_invalid_deadline_to_returns_400(self):
        """Bad deadline_to → 400, not 500."""
        client, db = TestDashboardHTTP()._client()
        resp = client.get(
            "/api/v1/eco/approvals/dashboard/items?deadline_to=xyz"
        )
        assert resp.status_code == 400
        assert "deadline_to" in resp.json()["detail"]
