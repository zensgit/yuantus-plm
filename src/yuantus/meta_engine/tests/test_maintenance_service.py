"""Tests for C5/C9 – Maintenance domain service layer."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock
import pytest

from yuantus.meta_engine.maintenance.models import (
    Equipment,
    EquipmentStatus,
    MaintenanceCategory,
    MaintenanceRequest,
    MaintenanceRequestState,
    MaintenanceType,
)
from yuantus.meta_engine.maintenance.service import MaintenanceService


class _MockQuery:
    """Minimal query mock that supports filter + order_by + all()."""

    def __init__(self, items):
        self._items = list(items)

    def filter(self, *_args, **_kwargs):
        # Return self to allow chaining; C9 tests use explicit list filtering
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


class TestCategories:

    def test_create_category(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        cat = svc.create_category(name="CNC Machines")
        assert cat.id
        assert cat.name == "CNC Machines"

    def test_create_subcategory(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        parent = svc.create_category(name="Machines")
        child = svc.create_category(name="CNC", parent_id=parent.id)
        assert child.parent_id == parent.id


# ---------------------------------------------------------------------------
# Equipment Tests
# ---------------------------------------------------------------------------


class TestEquipment:

    def test_create_equipment(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(
            name="CNC Mill #3",
            serial_number="SN-12345",
            manufacturer="Haas",
            model="VF-2",
            plant_code="PLT-A",
        )
        assert equip.id
        assert equip.name == "CNC Mill #3"
        assert equip.serial_number == "SN-12345"
        assert equip.status == "operational"

    def test_get_equipment(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Lathe #1")
        found = svc.get_equipment(equip.id)
        assert found is equip

    def test_update_equipment_status(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Press #1")
        updated = svc.update_equipment_status(equip.id, status="in_maintenance")
        assert updated.status == "in_maintenance"

    def test_update_equipment_status_invalid_raises(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Press #2")
        with pytest.raises(ValueError, match="Invalid status"):
            svc.update_equipment_status(equip.id, status="exploded")

    def test_update_equipment_status_not_found_raises(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.update_equipment_status("nonexistent", status="operational")


# ---------------------------------------------------------------------------
# Maintenance Request Tests
# ---------------------------------------------------------------------------


class TestMaintenanceRequests:

    def test_create_request_corrective(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill #1")
        req = svc.create_request(
            name="Fix spindle vibration",
            equipment_id=equip.id,
            maintenance_type="corrective",
            priority="high",
            description="Excessive vibration at 5000 RPM",
        )
        assert req.id
        assert req.state == "draft"
        assert req.maintenance_type == "corrective"
        assert req.priority == "high"

    def test_create_request_preventive(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Lathe #2")
        req = svc.create_request(
            name="Scheduled oil change",
            equipment_id=equip.id,
            maintenance_type="preventive",
        )
        assert req.maintenance_type == "preventive"

    def test_create_request_invalid_type_raises(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        with pytest.raises(ValueError, match="Invalid maintenance_type"):
            svc.create_request(
                name="Bad", equipment_id="e-1", maintenance_type="magical"
            )

    def test_create_request_invalid_priority_raises(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        with pytest.raises(ValueError, match="Invalid priority"):
            svc.create_request(
                name="Bad", equipment_id="e-1", priority="extreme"
            )

    def test_request_full_lifecycle(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill #2")
        req = svc.create_request(name="Repair belt", equipment_id=equip.id)
        assert req.state == "draft"

        svc.transition_request(req.id, target_state="submitted")
        assert req.state == "submitted"

        svc.transition_request(req.id, target_state="in_progress")
        assert req.state == "in_progress"
        assert req.started_at is not None

        svc.transition_request(
            req.id,
            target_state="done",
            resolution_note="Belt replaced",
        )
        assert req.state == "done"
        assert req.completed_at is not None
        assert req.resolution_note == "Belt replaced"

    def test_request_cancel_from_draft(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill #3")
        req = svc.create_request(name="Cancelled job", equipment_id=equip.id)
        svc.transition_request(req.id, target_state="cancelled")
        assert req.state == "cancelled"
        assert req.cancelled_at is not None

    def test_request_invalid_transition_raises(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill #4")
        req = svc.create_request(name="Test", equipment_id=equip.id)
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_request(req.id, target_state="done")

    def test_done_is_terminal(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill #5")
        req = svc.create_request(name="Terminal test", equipment_id=equip.id)
        svc.transition_request(req.id, target_state="submitted")
        svc.transition_request(req.id, target_state="in_progress")
        svc.transition_request(req.id, target_state="done")
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_request(req.id, target_state="in_progress")


# ---------------------------------------------------------------------------
# C9 – Equipment Readiness, Preventive Schedule, Queue Summary
# ---------------------------------------------------------------------------


class TestEquipmentReadiness:

    def test_readiness_all_operational(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        svc.create_equipment(name="Mill #1", plant_code="PLT-A")
        svc.create_equipment(name="Lathe #1", plant_code="PLT-A")
        summary = svc.get_equipment_readiness_summary(plant_code="PLT-A")
        assert summary["total_equipment"] == 2
        assert summary["operational"] == 2
        assert summary["readiness_pct"] == 100.0
        assert summary["needs_attention"] == []

    def test_readiness_with_degraded_equipment(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        svc.create_equipment(name="Mill OK", plant_code="PLT-A")
        down = svc.create_equipment(name="Mill DOWN", plant_code="PLT-A")
        svc.update_equipment_status(down.id, status="in_maintenance")
        summary = svc.get_equipment_readiness_summary(plant_code="PLT-A")
        assert summary["total_equipment"] == 2
        assert summary["operational"] == 1
        assert summary["readiness_pct"] == 50.0
        assert len(summary["needs_attention"]) == 1
        assert summary["needs_attention"][0]["name"] == "Mill DOWN"

    def test_readiness_empty_returns_zero(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        summary = svc.get_equipment_readiness_summary()
        assert summary["total_equipment"] == 0
        assert summary["readiness_pct"] == 0.0

    def test_readiness_workcenter_filter(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        svc.create_equipment(name="Mill A", workcenter_id="wc-1")
        svc.create_equipment(name="Mill B", workcenter_id="wc-2")
        summary = svc.get_equipment_readiness_summary(workcenter_id="wc-1")
        assert summary["total_equipment"] == 1
        assert summary["filters"]["workcenter_id"] == "wc-1"


class TestPreventiveSchedule:

    def test_overdue_preventive_detected(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Press #1")
        req = svc.create_request(
            name="PM Oil Change",
            equipment_id=equip.id,
            maintenance_type="preventive",
            due_date=datetime(2026, 1, 1),
        )
        svc.transition_request(req.id, target_state="submitted")
        ref = datetime(2026, 3, 18)
        result = svc.get_preventive_schedule(reference_date=ref)
        assert result["overdue_count"] == 1
        assert result["overdue"][0]["request_id"] == req.id
        assert result["overdue"][0]["days_overdue"] == 76

    def test_upcoming_preventive_detected(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Press #2")
        req = svc.create_request(
            name="PM Belt Replace",
            equipment_id=equip.id,
            maintenance_type="preventive",
            due_date=datetime(2026, 3, 25),
        )
        svc.transition_request(req.id, target_state="submitted")
        ref = datetime(2026, 3, 18)
        result = svc.get_preventive_schedule(reference_date=ref, window_days=30)
        assert result["upcoming_count"] == 1
        assert result["upcoming"][0]["days_until_due"] == 7

    def test_done_requests_excluded(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Lathe #3")
        req = svc.create_request(
            name="PM Completed",
            equipment_id=equip.id,
            maintenance_type="preventive",
            due_date=datetime(2026, 1, 1),
        )
        svc.transition_request(req.id, target_state="submitted")
        svc.transition_request(req.id, target_state="in_progress")
        svc.transition_request(req.id, target_state="done")
        result = svc.get_preventive_schedule(reference_date=datetime(2026, 3, 18))
        assert result["overdue_count"] == 0
        assert result["upcoming_count"] == 0

    def test_no_due_date_excluded(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill X")
        req = svc.create_request(
            name="PM No Date",
            equipment_id=equip.id,
            maintenance_type="preventive",
        )
        svc.transition_request(req.id, target_state="submitted")
        result = svc.get_preventive_schedule(reference_date=datetime(2026, 3, 18))
        assert result["overdue_count"] == 0
        assert result["upcoming_count"] == 0


class TestMaintenanceQueueSummary:

    def test_queue_includes_active_requests(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill #1")
        svc.create_request(name="Fix belt", equipment_id=equip.id, priority="high")
        svc.create_request(name="Replace filter", equipment_id=equip.id, priority="low")
        result = svc.get_maintenance_queue_summary()
        assert result["total_active"] == 2
        assert result["by_priority"]["high"] == 1
        assert result["by_priority"]["low"] == 1
        # Sorted: high before low
        assert result["queue"][0]["priority"] == "high"
        assert result["queue"][1]["priority"] == "low"

    def test_queue_excludes_done_and_cancelled(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Mill #2")
        r1 = svc.create_request(name="Active", equipment_id=equip.id)
        r2 = svc.create_request(name="Done", equipment_id=equip.id)
        svc.transition_request(r2.id, target_state="cancelled")
        result = svc.get_maintenance_queue_summary()
        assert result["total_active"] == 1
        assert result["queue"][0]["name"] == "Active"

    def test_queue_type_breakdown(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        equip = svc.create_equipment(name="Press #1")
        svc.create_request(
            name="Fix", equipment_id=equip.id, maintenance_type="corrective"
        )
        svc.create_request(
            name="PM", equipment_id=equip.id, maintenance_type="preventive"
        )
        result = svc.get_maintenance_queue_summary()
        assert result["by_type"]["corrective"] == 1
        assert result["by_type"]["preventive"] == 1

    def test_queue_workcenter_filter(self):
        session = _mock_session()
        svc = MaintenanceService(session)
        e1 = svc.create_equipment(name="Mill A", workcenter_id="wc-1")
        e2 = svc.create_equipment(name="Mill B", workcenter_id="wc-2")
        svc.create_request(name="R1", equipment_id=e1.id)
        svc.create_request(name="R2", equipment_id=e2.id)
        result = svc.get_maintenance_queue_summary(workcenter_id="wc-1")
        assert result["total_active"] == 1
        assert result["queue"][0]["name"] == "R1"
