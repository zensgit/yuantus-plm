from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.mbom_service import MBOMService
from yuantus.meta_engine.manufacturing.models import ManufacturingBOM, Routing


def test_release_mbom_not_found():
    session = MagicMock()
    session.get.return_value = None
    service = MBOMService(session)

    with pytest.raises(ValueError, match="MBOM not found: mbom-missing"):
        service.release_mbom("mbom-missing")


def test_release_mbom_requires_non_empty_structure():
    session = MagicMock()
    mbom = ManufacturingBOM(
        id="mbom-1",
        source_item_id="item-1",
        name="MBOM-1",
        version="1.0",
        state="draft",
        structure={},
    )
    session.get.return_value = mbom
    service = MBOMService(session)

    with pytest.raises(ValueError, match="structure is empty"):
        service.release_mbom("mbom-1")


def test_release_mbom_requires_released_routing():
    session = MagicMock()
    mbom = ManufacturingBOM(
        id="mbom-1",
        source_item_id="item-1",
        name="MBOM-1",
        version="1.0",
        state="draft",
        structure={"item": {"id": "item-1"}, "children": []},
    )
    session.get.return_value = mbom

    query = MagicMock()
    filtered = MagicMock()
    filtered.count.return_value = 0
    query.filter.return_value = filtered
    session.query.side_effect = lambda model: query if model == Routing else MagicMock()

    service = MBOMService(session)

    with pytest.raises(ValueError, match="at least one released routing"):
        service.release_mbom("mbom-1")


def test_release_and_reopen_mbom_success():
    session = MagicMock()
    mbom = ManufacturingBOM(
        id="mbom-1",
        source_item_id="item-1",
        name="MBOM-1",
        version="1.0",
        state="draft",
        structure={"item": {"id": "item-1"}, "children": []},
    )
    session.get.return_value = mbom

    query = MagicMock()
    filtered = MagicMock()
    filtered.count.return_value = 1
    query.filter.return_value = filtered
    session.query.side_effect = lambda model: query if model == Routing else MagicMock()

    service = MBOMService(session)
    released = service.release_mbom("mbom-1")
    assert released.state == "released"

    reopened = service.reopen_mbom("mbom-1")
    assert reopened.state == "draft"


def test_reopen_mbom_requires_released_state():
    session = MagicMock()
    mbom = ManufacturingBOM(
        id="mbom-1",
        source_item_id="item-1",
        name="MBOM-1",
        version="1.0",
        state="draft",
        structure={"item": {"id": "item-1"}},
    )
    session.get.return_value = mbom
    service = MBOMService(session)

    with pytest.raises(ValueError, match="Only released MBOM can be reopened"):
        service.reopen_mbom("mbom-1")
