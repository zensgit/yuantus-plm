from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.models import WorkCenter
from yuantus.meta_engine.manufacturing.workcenter_service import WorkCenterService


def test_create_workcenter_requires_code_and_name():
    session = MagicMock()
    service = WorkCenterService(session)

    with pytest.raises(ValueError, match="code is required"):
        service.create_workcenter({"name": "Assembly Center"})

    with pytest.raises(ValueError, match="name is required"):
        service.create_workcenter({"code": "WC-ASM"})


def test_create_workcenter_rejects_duplicate_code():
    session = MagicMock()
    service = WorkCenterService(session)
    service.get_workcenter_by_code = MagicMock(
        return_value=WorkCenter(id="wc-existing", code="WC-ASM", name="Existing")
    )

    with pytest.raises(ValueError, match="already exists"):
        service.create_workcenter({"code": "WC-ASM", "name": "Assembly Center"})


def test_create_workcenter_success_with_defaults():
    session = MagicMock()
    service = WorkCenterService(session)
    service.get_workcenter_by_code = MagicMock(return_value=None)

    created = service.create_workcenter({"code": "WC-PAINT", "name": "Paint Line"})

    assert created.code == "WC-PAINT"
    assert created.name == "Paint Line"
    assert created.capacity_per_day == 8.0
    assert created.scheduling_type == "finite"
    assert created.is_active is True
    session.add.assert_called_once_with(created)
    session.flush.assert_called_once()


def test_update_workcenter_rejects_code_conflict():
    session = MagicMock()
    service = WorkCenterService(session)
    current = WorkCenter(id="wc-1", code="WC-OLD", name="Old Name")
    service.get_workcenter_by_code = MagicMock(
        return_value=WorkCenter(id="wc-2", code="WC-NEW", name="Other")
    )

    with pytest.raises(ValueError, match="already exists"):
        service.update_workcenter(current, {"code": "WC-NEW"})


def test_update_workcenter_applies_changes():
    session = MagicMock()
    service = WorkCenterService(session)
    current = WorkCenter(id="wc-1", code="WC-OLD", name="Old Name", is_active=True)
    service.get_workcenter_by_code = MagicMock(return_value=None)

    updated = service.update_workcenter(
        current,
        {
            "code": "WC-NEW",
            "name": "New Name",
            "capacity_per_day": 12.5,
            "machine_count": 3,
            "is_active": False,
        },
    )

    assert updated.code == "WC-NEW"
    assert updated.name == "New Name"
    assert updated.capacity_per_day == 12.5
    assert updated.machine_count == 3
    assert updated.is_active is False
    session.add.assert_called_once_with(current)
    session.flush.assert_called_once()
