"""Tests for C12 – Generic approvals service layer."""

from datetime import datetime, timedelta
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
        assert req.rejection_reason is None
        assert req.decided_at is None
        assert req.decided_by_id is None

        history = svc.get_request_history(req.id, limit=10)
        assert history["total"] == 4
        assert history["latest"]["transition_type"] == "resubmitted"
        assert [event.get("transition_type") or event["event_type"] for event in history["events"]] == [
            "created",
            "submitted",
            "rejected",
            "resubmitted",
        ]

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

    def test_request_lifecycle_and_consumer_summary(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(
            title="Approve ECO-99",
            entity_type="eco",
            entity_id="eco-99",
            assigned_to_id=8,
            user_id=3,
        )
        svc.transition_request(req.id, target_state="pending")
        svc.transition_request(
            req.id,
            target_state="rejected",
            rejection_reason="Need cost impact",
            decided_by_id=8,
        )

        lifecycle = svc.get_request_lifecycle(req.id)
        summary = svc.get_request_consumer_summary(req.id)

        assert lifecycle["milestone_count"] >= 3
        assert lifecycle["latest"]["event_type"] == "rejected"
        assert summary["status"]["can_resubmit"] is True
        assert summary["proof"]["lifecycle"]["latest"]["event_type"] == "rejected"
        assert summary["proof"]["assignment"]["assigned_to_id"] == 8

    def test_request_history_and_consumer_summary_with_audit(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(
            title="Approve ECO-100",
            entity_type="eco",
            entity_id="eco-100",
            properties={"risk": "high"},
            user_id=7,
        )
        svc.transition_request(req.id, target_state="pending", decided_by_id=7)

        history = svc.get_request_history(req.id, limit=5)
        summary = svc.get_request_consumer_summary(
            req.id,
            include_history=True,
            history_limit=5,
        )
        pack_row = svc.get_request_pack_row(
            req.id,
            include_history=True,
            history_limit=5,
        )

        assert history["total"] == 2
        assert history["latest"]["to_state"] == "pending"
        assert summary["request"]["properties"]["risk"] == "high"
        assert summary["proof"]["audit"]["enabled"] is True
        assert summary["proof"]["audit"]["history_count"] == 2
        assert summary["proof"]["history_api"].endswith(f"/{req.id}/history")
        assert pack_row["found"] is True
        assert pack_row["status"]["requires_decision"] is True

    def test_request_pack_row_for_missing_request(self):
        session = _mock_session()
        svc = ApprovalService(session)

        row = svc.get_request_pack_row("missing", include_history=True, history_limit=2)

        assert row["found"] is False
        assert row["state"] == "not_found"
        assert row["proof"] is None


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
        assert summary["terminal_count"] == 1
        assert summary["unassigned_pending_count"] == 1
        assert summary["by_state"]["pending"] == 1
        assert summary["by_state"]["approved"] == 1
        assert summary["generated_at"].endswith("Z")

    def test_summary_empty(self):
        session = _mock_session()
        svc = ApprovalService(session)
        summary = svc.get_summary()
        assert summary["total"] == 0
        assert summary["pending"] == 0
        assert summary["terminal_count"] == 0


class TestApprovalExports:

    def test_requests_export_csv_is_case_insensitive(self):
        session = _mock_session()
        svc = ApprovalService(session)
        svc.create_request(title="Approve ECO", entity_type="eco")

        rendered = svc.export_requests(fmt="CSV")

        assert "id,title,category_id,entity_type,entity_id,state" in rendered

    def test_requests_export_json(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(
            title="Approve ECO-42",
            category_id="cat-1",
            entity_type="eco",
            entity_id="eco-42",
            assigned_to_id=7,
        )
        req.created_at = datetime.utcnow() - timedelta(hours=3)
        payload = svc.export_requests(fmt="json")
        assert payload["total"] == 1
        assert payload["pending_count"] == 0
        assert payload["terminal_count"] == 0
        assert payload["filters"]["entity_type"] is None
        assert payload["requests"][0]["id"] == req.id
        assert payload["generated_at"].endswith("Z")
        assert payload["requests"][0]["age_hours"] is not None
        assert payload["requests"][0]["age_hours"] >= 2.9
        assert payload["requests"][0]["is_assigned"] is True
        assert payload["requests"][0]["latest_event_type"] == "created"

    def test_requests_export_markdown(self):
        session = _mock_session()
        svc = ApprovalService(session)
        svc.create_request(title="Approve ECO-43", entity_type="eco")
        rendered = svc.export_requests(fmt="markdown", entity_type="eco")
        assert "# Approvals Requests Export" in rendered
        assert "## Filters" in rendered
        assert "pending_count" in rendered
        assert "Approve ECO-43" in rendered

    def test_summary_export_csv(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Approve BOM")
        svc.transition_request(req.id, target_state="pending")
        rendered = svc.export_summary(fmt="csv")
        assert "metric,value" in rendered
        assert "pending,1" in rendered

    def test_ops_report_bootstrap_ready(self):
        session = _mock_session()
        svc = ApprovalService(session)
        cat = svc.create_category(name="ECO")
        req = svc.create_request(
            title="Approve ECO",
            category_id=cat.id,
            entity_type="eco",
            entity_id="eco-1",
            assigned_to_id=9,
        )
        svc.transition_request(req.id, target_state="pending")
        svc.transition_request(req.id, target_state="approved", decided_by_id=9)
        report = svc.get_ops_report()
        assert report["category_coverage"] == 1.0
        assert report["entity_link_coverage"] == 1.0
        assert report["assignment_coverage"] == 1.0
        assert report["terminal_state_coverage"] == 1.0
        assert report["requires_decision_total"] == 0
        assert report["bootstrap_ready"] is True

    def test_ops_report_export_markdown(self):
        session = _mock_session()
        svc = ApprovalService(session)
        rendered = svc.export_ops_report(fmt="markdown")
        assert "# Approvals Ops Report" in rendered
        assert "bootstrap_ready" in rendered


class TestApprovalQueueHealth:

    def test_queue_health_flags_stale_pending_work(self):
        session = _mock_session()
        svc = ApprovalService(session)
        stale = svc.create_request(
            title="Stale review",
            priority="high",
            assigned_to_id=None,
        )
        stale.state = ApprovalState.PENDING.value
        stale.created_at = datetime.utcnow() - timedelta(hours=30)

        fresh = svc.create_request(
            title="Fresh review",
            priority="normal",
            assigned_to_id=5,
        )
        fresh.state = ApprovalState.PENDING.value
        fresh.created_at = datetime.utcnow() - timedelta(hours=2)

        approved = svc.create_request(title="Approved", priority="normal")
        approved.state = ApprovalState.APPROVED.value
        approved.created_at = datetime.utcnow() - timedelta(hours=1)

        health = svc.get_queue_health(stale_after_hours=24, warn_after_hours=4)

        assert health["total"] == 3
        assert health["pending"] == 2
        assert health["health_status"] == "degraded"
        assert "stale_pending_backlog" in health["risk_flags"]
        assert "unassigned_pending_work" in health["risk_flags"]
        assert health["pending_age"]["stale_count"] == 1
        assert health["pending_age"]["fresh_count"] == 1
        assert health["pending_age"]["oldest_hours"] >= 29.5
        assert health["operational_ready"] is False

    def test_queue_health_export_markdown(self):
        session = _mock_session()
        svc = ApprovalService(session)
        req = svc.create_request(title="Pending", assigned_to_id=None)
        req.state = ApprovalState.PENDING.value
        req.created_at = datetime.utcnow() - timedelta(hours=6)

        rendered = svc.export_queue_health(fmt="markdown")

        assert "# Approvals Queue Health" in rendered
        assert "health_status" in rendered
        assert "risk_flags" in rendered
