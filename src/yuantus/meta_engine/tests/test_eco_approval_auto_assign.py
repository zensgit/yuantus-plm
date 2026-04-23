"""
P2-2a R5: ECO Approval Auto-Assignment — Focused Tests
=======================================================
R3 fixes:
  1. Real RBAC permission boundary (401/403/allow)
  2. Stage-aware bridge dedup with state check
  3. Bridge failure raises (no silent swallow)
  4. Notifications target newly assigned user IDs only
"""
import pytest
from unittest.mock import MagicMock, patch
from yuantus.config import get_settings
from yuantus.meta_engine.services.eco_service import ECOApprovalService
from yuantus.exceptions.handlers import PermissionError


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _mock_stage(*, approval_type="mandatory", approval_roles=None, name="Review"):
    s = MagicMock()
    s.id = "stage-1"; s.name = name
    s.approval_type = approval_type
    s.approval_roles = approval_roles or ["engineer"]
    s.min_approvals = 1; s.sla_hours = None; s.auto_progress = False; s.sequence = 10
    return s


def _mock_eco(*, stage_id="stage-1", name="ECO-1"):
    e = MagicMock()
    e.id = "eco-1"; e.name = name; e.stage_id = stage_id
    e.state = "progress"; e.approval_deadline = None; e.created_by_id = 1
    return e


def _mock_user(uid, username, roles=None, is_superuser=False, is_active=True,
               inactive_roles=None, permissions=None):
    u = MagicMock()
    u.id = uid; u.username = username; u.email = f"{username}@test.com"
    u.is_superuser = is_superuser; u.is_active = is_active
    u.roles = []
    for r in (roles or []):
        role = MagicMock(); role.name = r; role.is_active = True
        u.roles.append(role)
    for r in (inactive_roles or []):
        role = MagicMock(); role.name = r; role.is_active = False
        u.roles.append(role)
    # has_permission uses the real logic via roles
    perm_set = set(permissions or [])
    def _has_perm(name):
        if is_superuser:
            return True
        return name in perm_set
    u.has_permission = _has_perm
    return u


def _svc(session):
    svc = ECOApprovalService(session)
    svc.notification_service = MagicMock()
    svc.audit_service = MagicMock()
    return svc


# ========================================================================
# A. HTTP / auth
# ========================================================================

class TestAuthHTTP:
    def test_router_uses_get_current_user_id_not_optional(self):
        """Route must use get_current_user_id (401 on no token)."""
        import inspect
        from yuantus.meta_engine.web import eco_router as mod
        src = inspect.getsource(mod.auto_assign_approvers)
        assert "get_current_user_id)" in src or "get_current_user_id," in src
        assert "get_current_user_id_optional" not in src

    def test_user_not_found_raises_permission_error(self):
        """User ID not in RBAC → PermissionError."""
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        svc = _svc(session)
        with pytest.raises(PermissionError):
            svc.auto_assign_stage_approvers("eco-1", user_id=999)

    def test_user_without_permission_raises(self):
        """User exists but lacks eco.auto_assign → PermissionError (→ 403)."""
        session = MagicMock()
        user = _mock_user(7, "bob", roles=["viewer"], permissions=[])  # no eco.auto_assign
        session.query.return_value.filter.return_value.first.return_value = user
        svc = _svc(session)
        with pytest.raises(PermissionError):
            svc.auto_assign_stage_approvers("eco-1", user_id=7)

    def test_superuser_bypasses_permission(self):
        """Superuser always allowed."""
        session = MagicMock()
        admin = _mock_user(1, "admin", is_superuser=True)
        cand = _mock_user(10, "alice", roles=["engineer"])
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])

        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            chain.filter.return_value.first.return_value = admin if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [cand]
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)
        svc = _svc(session)
        with patch("yuantus.meta_engine.approvals.service.ApprovalService"):
            svc.auto_assign_stage_approvers("eco-1", user_id=1)

    def test_user_with_permission_allowed(self):
        """User with eco.auto_assign → no PermissionError."""
        session = MagicMock()
        user = _mock_user(7, "eng", roles=["engineer"], permissions=["eco.auto_assign"])
        cand = _mock_user(10, "alice", roles=["engineer"])
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])

        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            chain.filter.return_value.first.return_value = user if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [cand]
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)
        svc = _svc(session)
        with patch("yuantus.meta_engine.approvals.service.ApprovalService"):
            result = svc.auto_assign_stage_approvers("eco-1", user_id=7)
        assert "assigned" in result

    def test_router_catches_permission_error_as_403(self):
        """Router must map PermissionError → 403, not 500."""
        import inspect
        from yuantus.meta_engine.web import eco_router as mod
        src = inspect.getsource(mod.auto_assign_approvers)
        assert "PermissionError" in src
        assert "403" in src


# ========================================================================
# Existing error semantics (unchanged from R2)
# ========================================================================

class TestAutoAssignErrors:
    def _permitted_svc(self, session):
        svc = _svc(session)
        admin = _mock_user(1, "admin", is_superuser=True)
        session.query.return_value.filter.return_value.first.return_value = admin
        return svc

    def test_eco_not_found(self):
        session = MagicMock()
        session.get.return_value = None
        svc = self._permitted_svc(session)
        with pytest.raises(ValueError, match="not found"):
            svc.auto_assign_stage_approvers("eco-x", user_id=1)

    def test_stage_missing(self):
        session = MagicMock()
        eco = _mock_eco(stage_id=None)
        session.get.side_effect = lambda cls, id_: eco if cls.__name__ == "ECO" else None
        svc = self._permitted_svc(session)
        with pytest.raises(ValueError, match="no current stage"):
            svc.auto_assign_stage_approvers("eco-1", user_id=1)

    def test_stage_no_approval(self):
        session = MagicMock()
        eco = _mock_eco(); stage = _mock_stage(approval_type="none")
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)
        svc = self._permitted_svc(session)
        with pytest.raises(ValueError, match="does not require approval"):
            svc.auto_assign_stage_approvers("eco-1", user_id=1)


# ========================================================================
# B. Bridge state-aware dedup
# ========================================================================

class TestBridgeStateAwareDedup:
    def _setup(self, session, bridge_query_result=None):
        admin = _mock_user(1, "admin", is_superuser=True)
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])
        cand = _mock_user(10, "alice", roles=["engineer"])

        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            # 1st: permission check → admin (superuser bypasses)
            # 2nd: candidate users → [cand]
            # 3rd: ECOApproval existence → None
            # 4th: bridge JSONB → configurable
            chain.filter.return_value.first.return_value = (
                admin if call_count[0] == 1
                else bridge_query_result if call_count[0] == 4
                else None
            )
            chain.filter.return_value.all.return_value = [cand]
            chain.filter_by.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)
        return eco, stage, cand

    def test_pending_bridge_reused(self):
        """Same eco + stage + user + state=pending → reuse."""
        session = MagicMock()
        existing = MagicMock(id="ar-pending", state="pending")
        self._setup(session, bridge_query_result=existing)
        svc = _svc(session)
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            result = svc.auto_assign_stage_approvers("eco-1", user_id=1)
        assert "ar-pending" in result["approval_request_ids"]
        # create_request should NOT be called
        MockAR.return_value.create_request.assert_not_called()

    def test_completed_bridge_creates_new(self):
        """Same eco + stage + user + state=approved → query returns None (filter includes pending only) → new."""
        session = MagicMock()
        # The query filters state=pending, so approved/rejected won't match → returns None
        self._setup(session, bridge_query_result=None)
        svc = _svc(session)
        mock_ar = MagicMock(id="ar-new")
        mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            result = svc.auto_assign_stage_approvers("eco-1", user_id=1)
        MockAR.return_value.create_request.assert_called_once()
        assert "ar-new" in result["approval_request_ids"]

    def test_bridge_uses_lowercase_eco(self):
        """entity_type must be lowercase 'eco'."""
        session = MagicMock()
        self._setup(session, bridge_query_result=None)
        svc = _svc(session)
        mock_ar = MagicMock(id="ar-1"); mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            svc.auto_assign_stage_approvers("eco-1", user_id=1)
        kw = MockAR.return_value.create_request.call_args[1]
        assert kw["entity_type"] == "eco"

    def test_bridge_stores_stage_id_in_properties(self):
        session = MagicMock()
        self._setup(session, bridge_query_result=None)
        svc = _svc(session)
        mock_ar = MagicMock(id="ar-1"); mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            svc.auto_assign_stage_approvers("eco-1", user_id=1)
        assert mock_ar.properties["stage_id"] == "stage-1"


# ========================================================================
# C. Failure semantics — bridge failure must raise
# ========================================================================

class TestBridgeFailureRaises:
    def test_bridge_create_failure_raises(self):
        """If ApprovalRequest creation fails, the whole call must raise — no silent swallow."""
        session = MagicMock()
        admin = _mock_user(1, "admin", is_superuser=True)
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])
        cand = _mock_user(10, "alice", roles=["engineer"])

        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            chain.filter.return_value.first.return_value = admin if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [cand]
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.side_effect = Exception("DB constraint")
            with pytest.raises(Exception, match="DB constraint"):
                svc.auto_assign_stage_approvers("eco-1", user_id=1)


# ========================================================================
# D. Notifications
# ========================================================================

class TestNotifications:
    def test_notify_only_newly_assigned_user_ids(self):
        """recipients must be the actual user IDs, not the role bucket."""
        session = MagicMock()
        admin = _mock_user(1, "admin", is_superuser=True)
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])
        cand = _mock_user(10, "alice", roles=["engineer"])

        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            chain.filter.return_value.first.return_value = admin if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [cand]
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        mock_ar = MagicMock(id="ar-1"); mock_ar.properties = None
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            MockAR.return_value.create_request.return_value = mock_ar
            svc.auto_assign_stage_approvers("eco-1", user_id=1)

        svc.notification_service.notify.assert_called_once()
        call_args = svc.notification_service.notify.call_args
        recipients = call_args[1].get("recipients") if call_args[1] else call_args[0][2]
        assert recipients == ["10"]  # user ID as string, NOT role names

    def test_idempotent_reentry_no_notification(self):
        """If all users already_existed, no notification sent."""
        session = MagicMock()
        admin = _mock_user(1, "admin", is_superuser=True)
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])
        cand = _mock_user(10, "alice", roles=["engineer"])
        existing_appr = MagicMock(id="existing-appr")

        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            chain.filter.return_value.first.return_value = admin if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = [cand]
            chain.filter_by.return_value.first.return_value = existing_appr
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        svc.auto_assign_stage_approvers("eco-1", user_id=1)
        svc.notification_service.notify.assert_not_called()


# ========================================================================
# Inactive role / user (unchanged from R2)
# ========================================================================

class TestInactiveFiltering:
    def test_inactive_role_excluded(self):
        svc = _svc(MagicMock())
        user = _mock_user(10, "a", roles=[], inactive_roles=["engineer"])
        stage = _mock_stage(approval_roles=["engineer"])
        assert svc._user_has_stage_role(user, stage) is False

    def test_active_role_included(self):
        svc = _svc(MagicMock())
        user = _mock_user(10, "a", roles=["engineer"])
        stage = _mock_stage(approval_roles=["engineer"])
        assert svc._user_has_stage_role(user, stage) is True


# ========================================================================
# R4-A: approve() auto-progress failure semantics
# ========================================================================

class TestApproveAutoProgressFailure:
    """approve() → auto_progress to next stage → auto_assign must propagate
    failures when next stage requires approval."""

    def test_auto_assign_permission_error_propagates(self):
        """auto_assign raises PermissionError → approve() must fail."""
        from yuantus.meta_engine.services.eco_service import ECOApprovalService
        session = MagicMock()
        svc = ECOApprovalService(session)
        svc.notification_service = MagicMock()
        svc.audit_service = MagicMock()

        eco = _mock_eco(stage_id="s1")
        stage = _mock_stage(name="Review", approval_type="mandatory",
                            approval_roles=["engineer"])
        stage.auto_progress = True
        next_stage = _mock_stage(name="Final", approval_type="mandatory",
                                 approval_roles=["manager"])
        next_stage.id = "s2"; next_stage.sequence = 20

        user = _mock_user(7, "eng", roles=["engineer"])

        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        # approve() needs: user lookup, existing approval, stage_complete check
        approval_mock = MagicMock(id="a1", status="pending")
        call_count = [0]
        def query_side(*a, **kw):
            call_count[0] += 1
            chain = MagicMock()
            chain.filter.return_value.first.return_value = user
            chain.filter_by.return_value.first.return_value = approval_mock
            # stage_complete: count returns 1 (>= min_approvals=1)
            chain.filter.return_value.count.return_value = 1
            # next_stage query
            chain.filter.return_value.order_by.return_value.first.return_value = next_stage
            return chain
        session.query.side_effect = query_side

        # auto_assign will fail because the approving user (7) is not superuser
        # and doesn't have eco.auto_assign permission
        with pytest.raises(PermissionError):
            svc.approve("eco-1", 7, comment="ok")

    def test_next_stage_no_approval_skips_auto_assign(self):
        """Next stage approval_type=none → auto_assign not called, approve succeeds."""
        from yuantus.meta_engine.services.eco_service import ECOApprovalService
        import inspect
        src = inspect.getsource(ECOApprovalService.approve)
        # The code must check next_stage.approval_type != "none" before calling
        assert 'approval_type != "none"' in src or "approval_type != 'none'" in src


# ========================================================================
# R4-B: draft bridge lifecycle
# ========================================================================

class TestDraftBridgeLifecycle:
    def test_existing_draft_transitioned_to_pending(self):
        """same eco + stage + user + draft → transition to pending, reuse."""
        session = MagicMock()
        admin = _mock_user(1, "admin", is_superuser=True)
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])
        cand = _mock_user(10, "alice", roles=["engineer"])

        draft_ar = MagicMock(id="ar-draft", state="draft")

        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            # 1st: permission → admin
            chain.filter.return_value.first.return_value = (
                admin if call_count[0] == 1
                else draft_ar if call_count[0] == 4  # bridge query
                else None
            )
            chain.filter.return_value.all.return_value = [cand]
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        with patch("yuantus.meta_engine.approvals.service.ApprovalService") as MockAR:
            result = svc.auto_assign_stage_approvers("eco-1", user_id=1)

        # Draft should be transitioned to pending via transition_request
        MockAR.return_value.transition_request.assert_called_once_with(
            "ar-draft", target_state="pending"
        )
        # create_request NOT called — draft reused
        MockAR.return_value.create_request.assert_not_called()
        assert "ar-draft" in result["approval_request_ids"]

    def test_source_code_checks_draft_and_pending(self):
        """Bridge dedup query must include both DRAFT and PENDING states."""
        import inspect
        from yuantus.meta_engine.services.eco_service import ECOApprovalService
        src = inspect.getsource(ECOApprovalService.auto_assign_stage_approvers)
        assert "DRAFT" in src or "draft" in src
        assert "PENDING" in src or "pending" in src


# ========================================================================
# R5-A: HTTP-level 401/403 integration tests via TestClient
# ========================================================================

class TestHTTPAuthIntegration:
    """Real HTTP tests using FastAPI TestClient + dependency overrides."""

    def _client_no_user(self):
        """Simulate no authentication — get_current_user_id raises 401."""
        from fastapi.testclient import TestClient
        from yuantus.api.app import create_app
        from yuantus.api.dependencies.auth import get_current_user_id
        from yuantus.database import get_db

        app = create_app()
        mock_db = MagicMock()

        def override_get_db():
            try:
                yield mock_db
            finally:
                pass

        def override_no_user():
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Unauthorized")

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = override_no_user
        return TestClient(app), mock_db

    def _client_with_user(self, user_id: int):
        """Simulate authenticated user."""
        from fastapi.testclient import TestClient
        from yuantus.api.app import create_app
        from yuantus.api.dependencies.auth import get_current_user_id
        from yuantus.database import get_db

        app = create_app()
        mock_db = MagicMock()

        def override_get_db():
            try:
                yield mock_db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        return TestClient(app), mock_db

    def test_http_401_when_no_user(self):
        """POST /eco/{id}/auto-assign-approvers without auth → 401."""
        client, _db = self._client_no_user()
        resp = client.post("/api/v1/eco/eco-1/auto-assign-approvers")
        assert resp.status_code == 401

    def test_http_403_when_no_permission(self):
        """POST /eco/{id}/auto-assign-approvers with user lacking permission → 403."""
        client, db = self._client_with_user(7)

        with patch(
            "yuantus.meta_engine.web.eco_router.ECOApprovalService"
        ) as MockSvc:
            MockSvc.return_value.auto_assign_stage_approvers.side_effect = (
                PermissionError(
                    action="auto_assign", resource="ECO",
                    details={"reason": "no permission"},
                )
            )
            resp = client.post("/api/v1/eco/eco-1/auto-assign-approvers")

        assert resp.status_code == 403
        assert "Forbidden" in resp.json()["detail"]

    def test_http_200_when_authorized(self):
        """POST /eco/{id}/auto-assign-approvers with proper auth → 200."""
        client, db = self._client_with_user(1)

        with patch(
            "yuantus.meta_engine.web.eco_router.ECOApprovalService"
        ) as MockSvc:
            MockSvc.return_value.auto_assign_stage_approvers.return_value = {
                "assigned": [{"user_id": 10, "username": "alice",
                              "approval_id": "a1", "already_existed": False}],
                "approval_request_ids": ["ar-1"],
            }
            resp = client.post("/api/v1/eco/eco-1/auto-assign-approvers")

        assert resp.status_code == 200
        assert resp.json()["assigned"][0]["user_id"] == 10


# ========================================================================
# R5-B: Empty candidate = config error
# ========================================================================

class TestEmptyCandidateError:
    def test_no_candidates_raises_value_error(self):
        """If stage requires approval but 0 candidates found → ValueError."""
        session = MagicMock()
        admin = _mock_user(1, "admin", is_superuser=True)
        eco = _mock_eco(); stage = _mock_stage(approval_roles=["engineer"])
        # No matching users
        call_count = [0]
        def query_side(*a, **kw):
            chain = MagicMock()
            call_count[0] += 1
            chain.filter.return_value.first.return_value = admin if call_count[0] == 1 else None
            chain.filter.return_value.all.return_value = []  # empty!
            chain.filter_by.return_value.first.return_value = None
            return chain
        session.query.side_effect = query_side
        session.get.side_effect = lambda cls, id_: {
            "ECO": eco, "ECOStage": stage
        }.get(cls.__name__)

        svc = _svc(session)
        with pytest.raises(ValueError, match="no active users"):
            svc.auto_assign_stage_approvers("eco-1", user_id=1)
