"""
P2-2b: Overdue Approval Escalation — Focused Tests
====================================================
Per acceptance checklist:
  - HTTP 401/403/200
  - overdue pending → escalation success
  - not overdue → no-op
  - same overdue repeated → idempotent
  - generic ApprovalRequest bridge created / queryable
  - bridge failure → whole call fails
  - notifications only to new escalated users
"""
import pytest
from unittest.mock import MagicMock, patch
from yuantus.meta_engine.services.eco_service import ECOApprovalService
from yuantus.exceptions.handlers import PermissionError


def _mock_user(uid, username, is_superuser=False, permissions=None):
    u = MagicMock()
    u.id = uid; u.username = username; u.email = f"{username}@test.com"
    u.is_superuser = is_superuser; u.is_active = True; u.roles = []
    perm_set = set(permissions or [])
    u.has_permission = lambda name: is_superuser or name in perm_set
    return u


def _svc(session):
    svc = ECOApprovalService(session)
    svc.notification_service = MagicMock()
    svc.audit_service = MagicMock()
    return svc


def _overdue_entry(eco_id="eco-1", stage_id="s1"):
    return {
        "eco_id": eco_id, "eco_name": f"ECO-{eco_id}",
        "stage_id": stage_id, "hours_overdue": 5.0,
    }


# ========================================================================
# HTTP 401/403/200
# ========================================================================

class TestHTTPAuth:
    def _client_no_user(self, monkeypatch):
        from fastapi.testclient import TestClient
        from yuantus.api.app import create_app
        from yuantus.api.dependencies.auth import get_current_user_id
        from yuantus.config import get_settings
        from yuantus.database import get_db
        monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")
        app = create_app()
        def no_db():
            try: yield MagicMock()
            finally: pass
        def no_user():
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Unauthorized")
        app.dependency_overrides[get_db] = no_db
        app.dependency_overrides[get_current_user_id] = no_user
        return TestClient(app)

    def _client_with_user(self, uid, monkeypatch):
        from fastapi.testclient import TestClient
        from yuantus.api.app import create_app
        from yuantus.api.dependencies.auth import (
            CurrentUser,
            get_current_user,
            get_current_user_id,
        )
        from yuantus.config import get_settings
        from yuantus.database import get_db
        monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")
        app = create_app()
        db = MagicMock()
        def override_db():
            try: yield db
            finally: pass
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            id=uid,
            tenant_id="tenant-1",
            org_id="org-1",
            username=f"user-{uid}",
            email=None,
            roles=[],
            is_superuser=(uid == 1),
        )
        app.dependency_overrides[get_current_user_id] = lambda: uid
        return TestClient(app), db

    def test_401_no_auth(self, monkeypatch):
        c = self._client_no_user(monkeypatch)
        resp = c.post("/api/v1/eco/approvals/escalate-overdue")
        assert resp.status_code == 401

    def test_403_no_permission(self, monkeypatch):
        c, db = self._client_with_user(7, monkeypatch)
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.escalate_overdue_approvals.side_effect = PermissionError(
                action="escalate_overdue", resource="ECO", details={})
            resp = c.post("/api/v1/eco/approvals/escalate-overdue")
        assert resp.status_code == 403

    def test_200_authorized(self, monkeypatch):
        c, db = self._client_with_user(1, monkeypatch)
        with patch("yuantus.meta_engine.web.eco_router.ECOApprovalService") as M:
            M.return_value.escalate_overdue_approvals.return_value = {"escalated": 0, "items": []}
            resp = c.post("/api/v1/eco/approvals/escalate-overdue")
        assert resp.status_code == 200


# ========================================================================
# Service logic
# ========================================================================

class TestEscalationLogic:
    def _setup_svc(self, session, overdue_list, pending_apprs, admins,
                   existing_eco_appr=None, bridge_result=None):
        """Wire mocks for the escalation method."""
        caller = _mock_user(1, "caller", is_superuser=True)
        eco = MagicMock(id="eco-1", name="ECO-1")
        stage = MagicMock(id="s1", name="Review", approval_type="mandatory")

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=overdue_list)

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            chain = MagicMock()
            # 1st: permission check → caller
            if call_count[0] == 1:
                chain.filter.return_value.first.return_value = caller
                return chain
            # admins query
            chain.filter.return_value.all.return_value = admins if call_count[0] == 2 else pending_apprs
            # pending approvals
            chain.filter_by.return_value.all.return_value = pending_apprs
            # existing ECOApproval check
            chain.filter_by.return_value.first.return_value = existing_eco_appr
            # bridge query
            chain.filter.return_value.first.return_value = bridge_result
            return chain

        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        return svc

    def test_overdue_pending_escalated(self):
        session = MagicMock()
        admin = _mock_user(99, "admin", is_superuser=True)
        pending = [MagicMock(user_id=10, status="pending")]
        svc = self._setup_svc(session, [_overdue_entry()], pending, [admin])
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            mock_ar = MagicMock(id="ar-esc"); mock_ar.properties = None
            MockAR.return_value.create_request.return_value = mock_ar
            result = svc.escalate_overdue_approvals(user_id=1)
        assert result["escalated"] == 1
        assert result["items"][0]["escalated"][0]["escalated_to_user_id"] == 99

    def test_not_overdue_noop(self):
        session = MagicMock()
        svc = _svc(session)
        caller = _mock_user(1, "admin", is_superuser=True)
        session.query.return_value.filter.return_value.first.return_value = caller
        session.query.return_value.filter.return_value.all.return_value = [caller]
        svc.list_overdue_approvals = MagicMock(return_value=[])
        result = svc.escalate_overdue_approvals(user_id=1)
        assert result["escalated"] == 0
        assert result["items"] == []

    def test_idempotent_repeated_call(self):
        """Same admin already has ECOApproval → no new ECOApproval,
        but bridge still runs to repair any missing ApprovalRequest."""
        session = MagicMock()
        admin = _mock_user(99, "admin", is_superuser=True)
        pending = [MagicMock(user_id=10, status="pending")]
        existing = MagicMock(id="already-there")
        svc = self._setup_svc(session, [_overdue_entry()], pending, [admin],
                              existing_eco_appr=existing)
        mock_ar = MagicMock(id="ar-repair"); mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            result = svc.escalate_overdue_approvals(user_id=1)
        # No NEW escalation (ECOApproval already existed)
        assert result["escalated"] == 0
        # But bridge was still called to repair/ensure consistency
        MockAR.return_value.create_request.assert_called_once()

    def test_permission_denied(self):
        session = MagicMock()
        user = _mock_user(7, "viewer", permissions=[])
        session.query.return_value.filter.return_value.first.return_value = user
        svc = _svc(session)
        with pytest.raises(PermissionError):
            svc.escalate_overdue_approvals(user_id=7)


# ========================================================================
# Bridge
# ========================================================================

class TestEscalationBridge:
    def test_bridge_created_with_lowercase_eco(self):
        session = MagicMock()
        admin = _mock_user(99, "admin", is_superuser=True)
        caller = _mock_user(1, "caller", is_superuser=True)
        eco = MagicMock(id="eco-1", name="ECO-1")
        stage = MagicMock(id="s1", name="Review", approval_type="mandatory")
        pending = [MagicMock(user_id=10, status="pending")]

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            chain = MagicMock()
            chain.filter.return_value.first.return_value = caller if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [admin] if call_count[0] == 2 else pending
            chain.filter_by.return_value.all.return_value = pending
            chain.filter_by.return_value.first.return_value = None  # no existing ECOApproval
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[_overdue_entry()])
        mock_ar = MagicMock(id="ar-esc"); mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            svc.escalate_overdue_approvals(user_id=1)
        kw = MockAR.return_value.create_request.call_args[1]
        assert kw["entity_type"] == "eco"
        assert kw["priority"] == "urgent"

    def test_bridge_failure_raises(self):
        session = MagicMock()
        admin = _mock_user(99, "admin", is_superuser=True)
        caller = _mock_user(1, "caller", is_superuser=True)
        eco = MagicMock(id="eco-1", name="ECO-1")
        stage = MagicMock(id="s1", name="Review", approval_type="mandatory")
        pending = [MagicMock(user_id=10, status="pending")]

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            chain = MagicMock()
            chain.filter.return_value.first.return_value = caller if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [admin] if call_count[0] == 2 else pending
            chain.filter_by.return_value.all.return_value = pending
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[_overdue_entry()])
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.side_effect = Exception("DB error")
            with pytest.raises(Exception, match="DB error"):
                svc.escalate_overdue_approvals(user_id=1)


# ========================================================================
# Notifications
# ========================================================================

class TestEscalationNotifications:
    def test_notify_only_newly_escalated_users(self):
        session = MagicMock()
        admin = _mock_user(99, "admin", is_superuser=True)
        caller = _mock_user(1, "caller", is_superuser=True)
        eco = MagicMock(id="eco-1", name="ECO-1")
        stage = MagicMock(id="s1", name="Review", approval_type="mandatory")
        pending = [MagicMock(user_id=10, status="pending")]

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            chain = MagicMock()
            chain.filter.return_value.first.return_value = caller if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [admin] if call_count[0] == 2 else pending
            chain.filter_by.return_value.all.return_value = pending
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[_overdue_entry()])
        mock_ar = MagicMock(id="ar-esc"); mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            svc.escalate_overdue_approvals(user_id=1)

        svc.notification_service.notify.assert_called_once()
        call_args = svc.notification_service.notify.call_args
        recipients = call_args[1].get("recipients") if call_args[1] else call_args[0][2]
        assert recipients == ["99"]  # admin user ID, not role bucket


# ========================================================================
# R2 fixes
# ========================================================================

class TestExistingApprovalBridgeRepair:
    """Fix 1: admin already has ECOApproval → still ensure bridge exists."""

    def test_existing_eco_approval_still_creates_bridge(self):
        session = MagicMock()
        admin = _mock_user(99, "admin", is_superuser=True)
        caller = _mock_user(1, "caller", is_superuser=True)
        eco = MagicMock(id="eco-1", name="ECO-1")
        stage = MagicMock(id="s1", name="Review", approval_type="mandatory")
        pending = [MagicMock(user_id=10, status="pending")]
        existing_eco_appr = MagicMock(id="existing-appr")

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            chain = MagicMock()
            chain.filter.return_value.first.return_value = caller if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [admin] if call_count[0] == 2 else pending
            chain.filter_by.return_value.all.return_value = pending
            # Admin ALREADY has ECOApproval
            chain.filter_by.return_value.first.return_value = existing_eco_appr
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[_overdue_entry()])
        mock_ar = MagicMock(id="ar-repair"); mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            result = svc.escalate_overdue_approvals(user_id=1)

        # Bridge create_request MUST still be called even though ECOApproval existed
        MockAR.return_value.create_request.assert_called_once()
        kw = MockAR.return_value.create_request.call_args[1]
        assert kw["entity_type"] == "eco"


class TestNonApprovalStageExcluded:
    """Fix 2: stage with approval_type='none' must be excluded from escalation."""

    def test_approval_type_none_skipped(self):
        session = MagicMock()
        admin = _mock_user(99, "admin", is_superuser=True)
        caller = _mock_user(1, "caller", is_superuser=True)
        eco = MagicMock(id="eco-1", name="ECO-1")
        # Stage does NOT require approval
        stage = MagicMock(id="s1", name="Informational", approval_type="none")

        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            chain = MagicMock()
            chain.filter.return_value.first.return_value = caller if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [admin]
            chain.filter_by.return_value.all.return_value = []
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        svc.list_overdue_approvals = MagicMock(return_value=[_overdue_entry()])
        result = svc.escalate_overdue_approvals(user_id=1)

        # Should be skipped — no escalation for non-approval stage
        assert result["escalated"] == 0
        svc.notification_service.notify.assert_not_called()
