"""Tests for C12 – Generic approvals service layer."""

from unittest.mock import MagicMock
import pytest

from yuantus.meta_engine.approvals.models import (
    ApprovalCategory,
    ApprovalRequest,
    ApprovalState,
)
from yuantus.meta_engine.approvals.service import ApprovalService


class _MockQuery:
    """Minimal query mock supporting filter + order_by + all()."""

    def __init__(self, items):
        self._items = list(items)

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self._items)


def _mock_session():
    session = MagicMock()
    _store = {}

    def mock_add(obj):
        _store[obj.id] = obj

    def mock_get(model, obj_id):
        obj = _store.get(obj_id)
        if obj and isinstance(obj, model):
            return obj
        return None

    def mock_flush():
        pass

    def mock_query(model):
        return _MockQuery(
            obj for obj in _store.values() if isinstance(obj, model)
        )

    session.add.side_effect = mock_add
    session.get.side_effect = mock_get
    session.flush.side_effect = mock_flush
    session.query.side_effect = mock_query
    session._store = _store
    return session


# ---------------------------------------------------------------------------
# Category Tests
# ---------------------------------------------------------------------------


class TestApprovalCategories:

    def test_create_category(self):
        session = _mock_session()
        svc = ApprovalService(session)
        cat = svc.create_category(name="ECO Approvals")
        assert cat.id
        assert cat.name == "ECO Approvals"

    def test_create_subcategory(self):
        session = _mock_session()
        svc = ApprovalService(session)
        parent = svc.create_category(name="Engineering")
        child = svc.create_category(name="Design Review", parent_id=parent.id)
        assert child.parent_id == parent.id


# ---------------------------------------------------------------------------
# Approval Request Tests
# ---------------------------------------------------------------------------


class TestApprovalRequests:

    def test_create_request(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(
            title="Approve ECO-2026-001",
            entity_type="eco",
            entity_id="eco-1",
            priority="high",
        )
        assert req.id
        assert req.state == "draft"
        assert req.priority == "high"
        assert req.entity_type == "eco"

    def test_create_request_invalid_priority(self):
        session = _mock_session()
        svc = ApprovalService(session)
        with pytest.raises(ValueError, match="Invalid priority"):
            svc.create_request(title="Bad", priority="extreme")

    def test_full_approval_lifecycle(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Approve PO-100")
        assert req.state == "draft"

        svc.transition_request(req.id, target_state="pending")
        assert req.state == "pending"
        assert req.submitted_at is not None

        svc.transition_request(req.id, target_state="approved", decided_by_id=42)
        assert req.state == "approved"
        assert req.decided_at is not None
        assert req.decided_by_id == 42

    def test_rejection_with_reason(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Approve BOM Change")
        svc.transition_request(req.id, target_state="pending")
        svc.transition_request(
            req.id,
            target_state="rejected",
            rejection_reason="Missing cost analysis",
        )
        assert req.state == "rejected"
        assert req.rejection_reason == "Missing cost analysis"

    def test_rejected_can_be_resubmitted(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Resubmittable")
        svc.transition_request(req.id, target_state="pending")
        svc.transition_request(req.id, target_state="rejected")
        # Resubmit
        svc.transition_request(req.id, target_state="pending")
        assert req.state == "pending"

    def test_cancel_from_draft(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Cancelled")
        svc.transition_request(req.id, target_state="cancelled")
        assert req.state == "cancelled"
        assert req.cancelled_at is not None

    def test_approved_is_terminal(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Terminal")
        svc.transition_request(req.id, target_state="pending")
        svc.transition_request(req.id, target_state="approved")
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_request(req.id, target_state="pending")

    def test_invalid_transition(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Direct approve")
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_request(req.id, target_state="approved")

    def test_transition_nonexistent_raises(self):
        session = _mock_session()
        svc = ApprovalService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.transition_request("no-such", target_state="pending")


# ---------------------------------------------------------------------------
# Summary Tests
# ---------------------------------------------------------------------------


class TestApprovalSummary:

    def test_summary_counts(self):
        session = _mock_session()
        svc = ApprovalService(session)
        r1 = svc.create_request(title="A", priority="high")
        r2 = svc.create_request(title="B", priority="normal")
        svc.transition_request(r1.id, target_state="pending")
        svc.transition_request(r2.id, target_state="pending")
        svc.transition_request(r2.id, target_state="approved")

        summary = svc.get_summary()
        assert summary["total"] == 2
        assert summary["pending"] == 1
        assert summary["by_state"]["pending"] == 1
        assert summary["by_state"]["approved"] == 1

    def test_summary_empty(self):
        session = _mock_session()
        svc = ApprovalService(session)
        summary = svc.get_summary()
        assert summary["total"] == 0
        assert summary["pending"] == 0
