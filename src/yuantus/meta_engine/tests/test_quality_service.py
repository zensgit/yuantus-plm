"""Tests for C4 – Quality domain service layer."""

from unittest.mock import MagicMock, patch
import pytest

from yuantus.meta_engine.quality.models import (
    QualityAlertState,
    QualityCheckResult,
    QualityCheckType,
    QualityPoint,
    QualityCheck,
    QualityAlert,
)
from yuantus.meta_engine.quality.service import QualityService


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

    session.add.side_effect = mock_add
    session.get.side_effect = mock_get
    session.flush.side_effect = mock_flush
    session._store = _store
    return session


class TestQualityPoints:

    def test_create_point_pass_fail(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(name="Visual Inspection", check_type="pass_fail")
        assert point.id
        assert point.name == "Visual Inspection"
        assert point.check_type == "pass_fail"
        assert point.trigger_on == "manual"

    def test_create_point_measure_with_thresholds(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(
            name="Diameter Check",
            check_type="measure",
            measure_min=9.5,
            measure_max=10.5,
            measure_unit="mm",
        )
        assert point.check_type == "measure"
        assert point.measure_min == 9.5
        assert point.measure_max == 10.5

    def test_create_point_invalid_check_type_raises(self):
        session = _mock_session()
        svc = QualityService(session)
        with pytest.raises(ValueError, match="Invalid check_type"):
            svc.create_point(name="Bad", check_type="invalid")

    def test_create_point_invalid_trigger_raises(self):
        session = _mock_session()
        svc = QualityService(session)
        with pytest.raises(ValueError, match="Invalid trigger_on"):
            svc.create_point(name="Bad", trigger_on="unknown")

    def test_get_point(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(name="Test Point")
        found = svc.get_point(point.id)
        assert found is point

    def test_update_point(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(name="Old Name")
        updated = svc.update_point(point.id, name="New Name", is_active=False)
        assert updated.name == "New Name"
        assert updated.is_active is False


class TestQualityChecks:

    def test_create_check_from_point(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(name="Pass/Fail", product_id="item-1")
        check = svc.create_check(point_id=point.id, source_document_ref="MO-001")
        assert check.point_id == point.id
        assert check.product_id == "item-1"
        assert check.check_type == "pass_fail"
        assert check.result == "none"

    def test_create_check_missing_point_raises(self):
        session = _mock_session()
        svc = QualityService(session)
        with pytest.raises(ValueError, match="not found"):
            svc.create_check(point_id="nonexistent")

    def test_record_pass_fail_result(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(name="Visual")
        check = svc.create_check(point_id=point.id)
        updated = svc.record_check_result(check.id, result="pass", note="Looks good")
        assert updated.result == "pass"
        assert updated.note == "Looks good"
        assert updated.checked_at is not None

    def test_record_measure_auto_evaluates_pass(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(
            name="Diameter",
            check_type="measure",
            measure_min=9.5,
            measure_max=10.5,
        )
        check = svc.create_check(point_id=point.id)
        updated = svc.record_check_result(check.id, result="none", measure_value=10.0)
        assert updated.result == "pass"

    def test_record_measure_auto_evaluates_fail(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(
            name="Diameter",
            check_type="measure",
            measure_min=9.5,
            measure_max=10.5,
        )
        check = svc.create_check(point_id=point.id)
        updated = svc.record_check_result(check.id, result="none", measure_value=12.0)
        assert updated.result == "fail"

    def test_record_invalid_result_raises(self):
        session = _mock_session()
        svc = QualityService(session)
        point = svc.create_point(name="Visual")
        check = svc.create_check(point_id=point.id)
        with pytest.raises(ValueError, match="Invalid result"):
            svc.record_check_result(check.id, result="banana")


class TestQualityAlerts:

    def test_create_alert(self):
        session = _mock_session()
        svc = QualityService(session)
        alert = svc.create_alert(
            name="Defect on Part X",
            description="Surface scratch detected",
            priority="high",
        )
        assert alert.id
        assert alert.state == "new"
        assert alert.priority == "high"

    def test_create_alert_invalid_priority_raises(self):
        session = _mock_session()
        svc = QualityService(session)
        with pytest.raises(ValueError, match="Invalid priority"):
            svc.create_alert(name="Bad", priority="extreme")

    def test_alert_transition_new_to_confirmed(self):
        session = _mock_session()
        svc = QualityService(session)
        alert = svc.create_alert(name="Issue")
        updated = svc.transition_alert(alert.id, target_state="confirmed")
        assert updated.state == "confirmed"
        assert updated.confirmed_at is not None

    def test_alert_full_lifecycle(self):
        session = _mock_session()
        svc = QualityService(session)
        alert = svc.create_alert(name="Lifecycle Test")
        svc.transition_alert(alert.id, target_state="confirmed")
        svc.transition_alert(alert.id, target_state="in_progress")
        svc.transition_alert(alert.id, target_state="resolved")
        svc.transition_alert(alert.id, target_state="closed")
        assert alert.state == "closed"
        assert alert.resolved_at is not None
        assert alert.closed_at is not None

    def test_alert_invalid_transition_raises(self):
        session = _mock_session()
        svc = QualityService(session)
        alert = svc.create_alert(name="Test")
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_alert(alert.id, target_state="resolved")

    def test_alert_closed_cannot_transition(self):
        session = _mock_session()
        svc = QualityService(session)
        alert = svc.create_alert(name="Test")
        svc.transition_alert(alert.id, target_state="closed")
        with pytest.raises(ValueError, match="Cannot transition"):
            svc.transition_alert(alert.id, target_state="new")
