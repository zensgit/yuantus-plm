"""Tests for BoxService (C17 PLM Box Bootstrap)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from yuantus.meta_engine.box.models import BoxContent, BoxItem, BoxState, BoxType
from yuantus.meta_engine.box.service import BoxService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session():
    session = MagicMock()
    added = []
    session.add.side_effect = lambda obj: added.append(obj)
    session.flush.return_value = None
    session._added = added
    return session


def _make_box(box_id="box-1", name="Test Box", box_type="box", state="draft"):
    box = MagicMock(spec=BoxItem)
    box.id = box_id
    box.name = name
    box.box_type = box_type
    box.state = state
    box.description = None
    box.width = 300.0
    box.height = 200.0
    box.depth = 150.0
    box.dimension_unit = "mm"
    box.tare_weight = 0.5
    box.max_gross_weight = 10.0
    box.weight_unit = "kg"
    box.material = "cardboard"
    box.barcode = "1234567890"
    box.max_quantity = 50
    box.cost = 2.5
    box.product_id = None
    box.is_active = True
    box.properties = None
    box.created_by_id = None
    return box


# ---------------------------------------------------------------------------
# TestBoxCRUD
# ---------------------------------------------------------------------------


class TestBoxCRUD:
    def test_create_box(self):
        session = _mock_session()
        service = BoxService(session)

        box = service.create_box(name="Shipping Box", box_type="carton")

        assert box.name == "Shipping Box"
        assert box.box_type == "carton"
        assert box.state == "draft"
        assert session.add.called
        assert session.flush.called

    def test_get_box(self):
        session = _mock_session()
        fake_box = _make_box()
        session.get.return_value = fake_box

        service = BoxService(session)
        result = service.get_box("box-1")

        assert result is fake_box
        session.get.assert_called_once_with(BoxItem, "box-1")

    def test_list_with_filters(self):
        session = _mock_session()
        fake_box = _make_box(box_type="pallet", state="active")
        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [fake_box]

        service = BoxService(session)
        result = service.list_boxes(box_type="pallet", state="active")

        assert len(result) == 1
        assert result[0].box_type == "pallet"

    def test_update_box(self):
        session = _mock_session()
        fake_box = _make_box()
        session.get.return_value = fake_box

        service = BoxService(session)
        result = service.update_box("box-1", name="Updated Box", material="wood")

        assert result is not None
        assert fake_box.name == "Updated Box"
        assert fake_box.material == "wood"

    def test_create_invalid_type(self):
        session = _mock_session()
        service = BoxService(session)

        with pytest.raises(ValueError, match="Invalid box_type"):
            service.create_box(name="Bad", box_type="spaceship")


# ---------------------------------------------------------------------------
# TestBoxState
# ---------------------------------------------------------------------------


class TestBoxState:
    def test_draft_to_active(self):
        session = _mock_session()
        fake_box = _make_box(state="draft")
        session.get.return_value = fake_box

        service = BoxService(session)
        result = service.transition_state("box-1", "active")

        assert result.state == "active"

    def test_active_to_archived(self):
        session = _mock_session()
        fake_box = _make_box(state="active")
        session.get.return_value = fake_box

        service = BoxService(session)
        result = service.transition_state("box-1", "archived")

        assert result.state == "archived"

    def test_invalid_transition(self):
        session = _mock_session()
        fake_box = _make_box(state="draft")
        session.get.return_value = fake_box

        service = BoxService(session)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.transition_state("box-1", "archived")

    def test_archived_terminal(self):
        session = _mock_session()
        fake_box = _make_box(state="archived")
        session.get.return_value = fake_box

        service = BoxService(session)
        with pytest.raises(ValueError, match="Cannot transition"):
            service.transition_state("box-1", "active")


# ---------------------------------------------------------------------------
# TestBoxContents
# ---------------------------------------------------------------------------


class TestBoxContents:
    def test_add_content(self):
        session = _mock_session()
        fake_box = _make_box()
        session.get.return_value = fake_box

        service = BoxService(session)
        content = service.add_content("box-1", item_id="item-42", quantity=5.0)

        assert content.box_id == "box-1"
        assert content.item_id == "item-42"
        assert content.quantity == 5.0
        assert session.add.called

    def test_list_contents(self):
        session = _mock_session()
        fake_content = MagicMock(spec=BoxContent)
        fake_content.box_id = "box-1"
        fake_content.item_id = "item-1"
        fake_content.quantity = 3.0

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [fake_content]

        service = BoxService(session)
        result = service.list_contents("box-1")

        assert len(result) == 1
        assert result[0].item_id == "item-1"

    def test_remove_content(self):
        session = _mock_session()
        fake_content = MagicMock(spec=BoxContent)
        session.get.return_value = fake_content

        service = BoxService(session)
        assert service.remove_content("content-1") is True
        session.delete.assert_called_once_with(fake_content)
