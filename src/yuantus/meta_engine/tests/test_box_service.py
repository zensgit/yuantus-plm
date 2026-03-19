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


# ---------------------------------------------------------------------------
# TestBoxAnalytics (C20)
# ---------------------------------------------------------------------------


class TestBoxAnalytics:
    def _session_with_boxes(self, boxes):
        """Session whose query(BoxItem).all() returns *boxes*."""
        session = _mock_session()
        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.all.return_value = boxes
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        return session

    def test_overview(self):
        boxes = [
            _make_box(box_id="b1", state="draft", box_type="box"),
            _make_box(box_id="b2", state="active", box_type="carton"),
            _make_box(box_id="b3", state="active", box_type="box"),
        ]
        boxes[0].cost = 2.0
        boxes[1].cost = 3.5
        boxes[2].cost = None
        boxes[0].is_active = True
        boxes[1].is_active = True
        boxes[2].is_active = False

        session = self._session_with_boxes(boxes)
        service = BoxService(session)
        result = service.overview()

        assert result["total"] == 3
        assert result["active"] == 2
        assert result["by_state"]["draft"] == 1
        assert result["by_state"]["active"] == 2
        assert result["by_type"]["box"] == 2
        assert result["by_type"]["carton"] == 1
        assert result["total_cost"] == 5.5

    def test_overview_empty(self):
        session = self._session_with_boxes([])
        service = BoxService(session)
        result = service.overview()

        assert result["total"] == 0
        assert result["active"] == 0
        assert result["by_state"] == {}
        assert result["total_cost"] == 0.0

    def test_material_analytics(self):
        boxes = [
            _make_box(box_id="b1"),
            _make_box(box_id="b2"),
            _make_box(box_id="b3"),
        ]
        boxes[0].material = "cardboard"
        boxes[1].material = "wood"
        boxes[2].material = None

        session = self._session_with_boxes(boxes)
        service = BoxService(session)
        result = service.material_analytics()

        assert result["total"] == 3
        assert result["by_material"]["cardboard"] == 1
        assert result["by_material"]["wood"] == 1
        assert result["no_material"] == 1

    def test_contents_summary(self):
        session = _mock_session()
        fake_box = _make_box()
        session.get.return_value = fake_box

        c1 = MagicMock(spec=BoxContent)
        c1.item_id = "item-1"
        c1.quantity = 5.0
        c1.lot_serial = "LOT-001"

        c2 = MagicMock(spec=BoxContent)
        c2.item_id = "item-2"
        c2.quantity = 3.0
        c2.lot_serial = None

        c3 = MagicMock(spec=BoxContent)
        c3.item_id = "item-1"
        c3.quantity = 2.0
        c3.lot_serial = "LOT-002"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1, c2, c3]

        service = BoxService(session)
        result = service.contents_summary("box-1")

        assert result["box_id"] == "box-1"
        assert result["total_lines"] == 3
        assert result["distinct_items"] == 2
        assert result["total_quantity"] == 10.0
        assert result["has_lot_serial"] == 2

    def test_contents_summary_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.contents_summary("nonexistent")

    def test_export_overview(self):
        boxes = [_make_box(box_id="b1")]
        boxes[0].cost = 10.0
        boxes[0].material = "plastic"

        session = self._session_with_boxes(boxes)
        service = BoxService(session)
        result = service.export_overview()

        assert "overview" in result
        assert "material_analytics" in result
        assert result["overview"]["total"] == 1
        assert result["material_analytics"]["by_material"]["plastic"] == 1

    def test_export_contents(self):
        session = _mock_session()
        fake_box = _make_box()
        session.get.return_value = fake_box

        c1 = MagicMock(spec=BoxContent)
        c1.id = "c-1"
        c1.item_id = "item-1"
        c1.quantity = 4.0
        c1.lot_serial = None
        c1.note = "fragile"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1]

        service = BoxService(session)
        result = service.export_contents("box-1")

        assert result["box_id"] == "box-1"
        assert result["total_lines"] == 1
        assert result["total_quantity"] == 4.0
        assert len(result["contents"]) == 1
        assert result["contents"][0]["note"] == "fragile"

    def test_export_contents_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.export_contents("nonexistent")


# ---------------------------------------------------------------------------
# TestOpsReport (C23)
# ---------------------------------------------------------------------------


class TestOpsReport:
    def _session_with_boxes(self, boxes):
        """Session whose query(BoxItem).all() returns *boxes*."""
        session = _mock_session()
        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.all.return_value = boxes
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        return session

    def test_transition_summary(self):
        boxes = [
            _make_box(box_id="b1", state="draft"),
            _make_box(box_id="b2", state="draft"),
            _make_box(box_id="b3", state="active"),
            _make_box(box_id="b4", state="archived"),
        ]

        session = self._session_with_boxes(boxes)
        service = BoxService(session)
        result = service.transition_summary()

        assert result["total"] == 4
        assert result["by_state"]["draft"] == 2
        assert result["by_state"]["active"] == 1
        assert result["by_state"]["archived"] == 1
        assert result["draft_to_active_eligible"] == 2
        assert result["active_to_archive_eligible"] == 1

    def test_transition_summary_empty(self):
        session = self._session_with_boxes([])
        service = BoxService(session)
        result = service.transition_summary()

        assert result["total"] == 0
        assert result["by_state"] == {}
        assert result["draft_to_active_eligible"] == 0
        assert result["active_to_archive_eligible"] == 0

    def test_active_archive_breakdown(self):
        boxes = [
            _make_box(box_id="b1", state="active", box_type="box"),
            _make_box(box_id="b2", state="active", box_type="carton"),
            _make_box(box_id="b3", state="archived", box_type="box"),
            _make_box(box_id="b4", state="draft", box_type="pallet"),
        ]
        boxes[0].cost = 5.0
        boxes[1].cost = 3.0
        boxes[2].cost = 2.0
        boxes[3].cost = 1.0

        session = self._session_with_boxes(boxes)
        service = BoxService(session)
        result = service.active_archive_breakdown()

        assert result["active"]["count"] == 2
        assert result["active"]["total_cost"] == 8.0
        assert result["active"]["by_type"]["box"] == 1
        assert result["active"]["by_type"]["carton"] == 1
        assert result["archived"]["count"] == 1
        assert result["archived"]["total_cost"] == 2.0
        assert result["archived"]["by_type"]["box"] == 1

    def test_active_archive_breakdown_no_archived(self):
        boxes = [
            _make_box(box_id="b1", state="active", box_type="box"),
            _make_box(box_id="b2", state="draft", box_type="carton"),
        ]
        boxes[0].cost = 10.0
        boxes[1].cost = 5.0

        session = self._session_with_boxes(boxes)
        service = BoxService(session)
        result = service.active_archive_breakdown()

        assert result["active"]["count"] == 1
        assert result["active"]["total_cost"] == 10.0
        assert result["archived"]["count"] == 0
        assert result["archived"]["total_cost"] == 0.0
        assert result["archived"]["by_type"] == {}

    def test_ops_report_draft(self):
        session = _mock_session()
        fake_box = _make_box(state="draft")
        session.get.return_value = fake_box

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock

        c1 = MagicMock(spec=BoxContent)
        c1.quantity = 5.0
        c2 = MagicMock(spec=BoxContent)
        c2.quantity = 3.0
        query_mock.all.return_value = [c1, c2]

        service = BoxService(session)
        result = service.ops_report("box-1")

        assert result["box_id"] == "box-1"
        assert result["name"] == "Test Box"
        assert result["state"] == "draft"
        assert result["can_activate"] is True
        assert result["can_archive"] is False
        assert result["is_terminal"] is False
        assert result["contents_count"] == 2
        assert result["total_quantity"] == 8.0
        assert result["material"] == "cardboard"
        assert result["cost"] == 2.5

    def test_ops_report_active(self):
        session = _mock_session()
        fake_box = _make_box(state="active")
        session.get.return_value = fake_box

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = []

        service = BoxService(session)
        result = service.ops_report("box-1")

        assert result["state"] == "active"
        assert result["can_activate"] is False
        assert result["can_archive"] is True
        assert result["is_terminal"] is False
        assert result["contents_count"] == 0
        assert result["total_quantity"] == 0.0

    def test_ops_report_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.ops_report("nonexistent")

    def test_export_ops_report(self):
        boxes = [
            _make_box(box_id="b1", state="draft"),
            _make_box(box_id="b2", state="active"),
            _make_box(box_id="b3", state="archived"),
        ]
        boxes[0].cost = 1.0
        boxes[1].cost = 2.0
        boxes[2].cost = 3.0

        session = self._session_with_boxes(boxes)
        service = BoxService(session)
        result = service.export_ops_report()

        assert "transition_summary" in result
        assert "active_archive_breakdown" in result

        ts = result["transition_summary"]
        assert ts["total"] == 3
        assert ts["draft_to_active_eligible"] == 1
        assert ts["active_to_archive_eligible"] == 1

        aab = result["active_archive_breakdown"]
        assert aab["active"]["count"] == 1
        assert aab["active"]["total_cost"] == 2.0
        assert aab["archived"]["count"] == 1
        assert aab["archived"]["total_cost"] == 3.0
