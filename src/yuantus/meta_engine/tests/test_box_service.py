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


# ---------------------------------------------------------------------------
# TestReconciliationAudit (C26)
# ---------------------------------------------------------------------------


class TestReconciliationAudit:
    def _session_with_boxes_and_contents(self, boxes, contents_map=None):
        """Session whose query(BoxItem).all() returns boxes and list_contents is routed via contents_map."""
        session = _mock_session()
        _contents_map = contents_map or {}

        def mock_query(model):
            q = MagicMock()
            if model is BoxItem:
                q.all.return_value = boxes
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is BoxContent:
                # For list_contents: filter by box_id
                def content_filter(*args, **kwargs):
                    fq = MagicMock()
                    # Return all contents for simplicity; per-box filtering via contents_map
                    fq.all.return_value = []
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = content_filter
                q.order_by.return_value = q
                q.all.return_value = []
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        # Support session.get for per-box reconciliation
        def get_side_effect(model, pk):
            if model is BoxItem:
                return next((b for b in boxes if b.id == pk), None)
            return None

        session.get.side_effect = get_side_effect

        return session

    def test_reconciliation_overview(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.barcode = "BC001"
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0
        b1.tare_weight = 0.5
        b1.max_gross_weight = 10.0

        b2 = _make_box(box_id="b2", state="draft")
        b2.barcode = None
        b2.width = None
        b2.height = None
        b2.depth = None
        b2.tare_weight = None
        b2.max_gross_weight = None

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)
        result = service.reconciliation_overview()

        assert result["total"] == 2
        assert result["without_contents"] == 2  # no contents mocked
        assert result["with_barcode"] == 1
        assert result["without_barcode"] == 1
        assert result["with_dimensions"] == 1
        assert result["with_weight"] == 1
        # completeness: (1 barcode + 1 dims + 1 weight) / (2*3) = 3/6 = 50.0%
        assert result["completeness_pct"] == 50.0

    def test_reconciliation_overview_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.reconciliation_overview()

        assert result["total"] == 0
        assert result["completeness_pct"] == 0.0

    def test_audit_summary(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.material = "cardboard"
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0
        b1.cost = 2.5

        b2 = _make_box(box_id="b2", state="draft")
        b2.material = None
        b2.width = None
        b2.height = None
        b2.depth = None
        b2.cost = None

        b3 = _make_box(box_id="b3", state="archived")
        b3.material = "wood"
        b3.width = 200.0
        b3.height = 150.0
        b3.depth = 100.0
        b3.cost = 5.0

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.audit_summary()

        assert result["total"] == 3
        assert result["no_material"] == 1
        assert "b2" in result["no_material_ids"]
        assert result["no_dimensions"] == 1
        assert "b2" in result["no_dimensions_ids"]
        assert result["no_cost"] == 1
        assert "b2" in result["no_cost_ids"]

    def test_audit_summary_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.audit_summary()

        assert result["total"] == 0
        assert result["no_material"] == 0
        assert result["no_dimensions"] == 0
        assert result["no_cost"] == 0
        assert result["archived_with_contents"] == 0

    def test_box_reconciliation(self):
        session = _mock_session()
        box = _make_box(state="active")
        box.material = "cardboard"
        box.width = 100.0
        box.height = 80.0
        box.depth = 50.0
        box.tare_weight = 0.5
        box.max_gross_weight = None
        box.barcode = "BC001"
        box.cost = 2.5
        session.get.return_value = box

        c1 = MagicMock(spec=BoxContent)
        c1.quantity = 5.0
        c2 = MagicMock(spec=BoxContent)
        c2.quantity = 3.0

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1, c2]

        service = BoxService(session)
        result = service.box_reconciliation("box-1")

        assert result["box_id"] == "box-1"
        assert result["has_material"] is True
        assert result["has_dimensions"] is True
        assert result["has_weight"] is True
        assert result["has_barcode"] is True
        assert result["has_cost"] is True
        assert result["checks_passed"] == 5
        assert result["checks_total"] == 5
        assert result["contents_count"] == 2
        assert result["total_quantity"] == 8.0

    def test_box_reconciliation_incomplete(self):
        session = _mock_session()
        box = _make_box(state="draft")
        box.material = None
        box.width = None
        box.height = None
        box.depth = None
        box.tare_weight = None
        box.max_gross_weight = None
        box.barcode = None
        box.cost = None
        session.get.return_value = box

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = []

        service = BoxService(session)
        result = service.box_reconciliation("box-1")

        assert result["has_material"] is False
        assert result["has_dimensions"] is False
        assert result["has_weight"] is False
        assert result["has_barcode"] is False
        assert result["has_cost"] is False
        assert result["checks_passed"] == 0
        assert result["contents_count"] == 0

    def test_box_reconciliation_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.box_reconciliation("nonexistent")

    def test_export_box_reconciliation(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.barcode = "BC001"
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0
        b1.tare_weight = 0.5
        b1.max_gross_weight = 10.0
        b1.material = "cardboard"
        b1.cost = 2.5

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.export_box_reconciliation()

        assert "reconciliation_overview" in result
        assert "audit_summary" in result
        assert result["reconciliation_overview"]["total"] == 1
        assert result["audit_summary"]["total"] == 1


# ---------------------------------------------------------------------------
# TestCapacityCompliance (C29)
# ---------------------------------------------------------------------------


class TestCapacityCompliance:
    def _session_with_boxes_and_contents(self, boxes, contents_map=None):
        """Session whose query(BoxItem).all() returns boxes and list_contents is routed via contents_map."""
        session = _mock_session()
        _contents_map = contents_map or {}

        def mock_query(model):
            q = MagicMock()
            if model is BoxItem:
                q.all.return_value = boxes
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is BoxContent:
                def content_filter(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = []
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = content_filter
                q.order_by.return_value = q
                q.all.return_value = []
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        def get_side_effect(model, pk):
            if model is BoxItem:
                return next((b for b in boxes if b.id == pk), None)
            return None

        session.get.side_effect = get_side_effect

        return session

    def test_capacity_overview(self):
        b1 = _make_box(box_id="b1")
        b1.max_quantity = 10
        b1.max_gross_weight = 50.0

        b2 = _make_box(box_id="b2")
        b2.max_quantity = 5
        b2.max_gross_weight = None

        b3 = _make_box(box_id="b3")
        b3.max_quantity = None
        b3.max_gross_weight = 20.0

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.capacity_overview()

        assert result["total"] == 3
        assert result["with_max_quantity"] == 2
        assert result["with_weight_limit"] == 2
        # No contents mocked -> fill rate = 0 for both boxes with max_quantity
        assert result["average_fill_rate"] == 0.0
        assert result["bands"]["low"] == 2  # 0% fill -> low band
        assert result["bands"]["medium"] == 0
        assert result["bands"]["high"] == 0

    def test_capacity_overview_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.capacity_overview()

        assert result["total"] == 0
        assert result["with_max_quantity"] == 0
        assert result["with_weight_limit"] == 0
        assert result["average_fill_rate"] == 0.0
        assert result["bands"] == {"high": 0, "medium": 0, "low": 0}

    def test_compliance_summary(self):
        # b1: fully compliant (has dims, tare_weight, no contents so no weight-limit issue)
        b1 = _make_box(box_id="b1")
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0
        b1.tare_weight = 0.5
        b1.max_gross_weight = 10.0
        b1.max_quantity = 50

        # b2: missing dimensions, missing tare_weight
        b2 = _make_box(box_id="b2")
        b2.width = None
        b2.height = None
        b2.depth = None
        b2.tare_weight = None
        b2.max_gross_weight = None
        b2.max_quantity = None

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)
        result = service.compliance_summary()

        assert result["total"] == 2
        assert result["missing_dimensions"] == 1
        assert result["missing_weight"] == 1
        assert result["compliant"] == 1
        assert result["non_compliant"] == 1

    def test_compliance_summary_all_compliant(self):
        b1 = _make_box(box_id="b1")
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0
        b1.tare_weight = 0.5
        b1.max_gross_weight = 10.0
        b1.max_quantity = 50

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.compliance_summary()

        assert result["total"] == 1
        assert result["missing_dimensions"] == 0
        assert result["missing_weight"] == 0
        assert result["exceeding_weight_limit"] == 0
        assert result["over_capacity"] == 0
        assert result["compliant"] == 1
        assert result["non_compliant"] == 0

    def test_box_capacity(self):
        session = _mock_session()
        box = _make_box(state="active")
        box.max_quantity = 10
        box.max_gross_weight = 50.0
        box.tare_weight = 1.0
        box.width = 100.0
        box.height = 80.0
        box.depth = 50.0
        session.get.return_value = box

        c1 = MagicMock(spec=BoxContent)
        c1.quantity = 5.0
        c2 = MagicMock(spec=BoxContent)
        c2.quantity = 3.0

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1, c2]

        service = BoxService(session)
        result = service.box_capacity("box-1")

        assert result["box_id"] == "box-1"
        assert result["max_quantity"] == 10
        assert result["contents_count"] == 2
        assert result["fill_pct"] == 20.0
        assert result["has_weight_limit"] is True
        assert result["tare_weight"] == 1.0
        assert result["max_gross_weight"] == 50.0
        assert result["dimension_complete"] is True
        assert result["compliance_checks"]["missing_dimensions"] is False
        assert result["compliance_checks"]["missing_weight"] is False
        assert result["compliance_checks"]["over_capacity"] is False

    def test_box_capacity_incomplete(self):
        session = _mock_session()
        box = _make_box(state="draft")
        box.max_quantity = None
        box.max_gross_weight = None
        box.tare_weight = None
        box.width = None
        box.height = None
        box.depth = None
        session.get.return_value = box

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = []

        service = BoxService(session)
        result = service.box_capacity("box-1")

        assert result["box_id"] == "box-1"
        assert result["max_quantity"] is None
        assert result["contents_count"] == 0
        assert result["fill_pct"] == 0.0
        assert result["has_weight_limit"] is False
        assert result["tare_weight"] is None
        assert result["max_gross_weight"] is None
        assert result["dimension_complete"] is False
        assert result["compliance_checks"]["missing_dimensions"] is True
        assert result["compliance_checks"]["missing_weight"] is True
        assert result["compliance_checks"]["over_capacity"] is False

    def test_box_capacity_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.box_capacity("nonexistent")

    def test_export_capacity(self):
        b1 = _make_box(box_id="b1")
        b1.max_quantity = 10
        b1.max_gross_weight = 50.0
        b1.tare_weight = 1.0
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.export_capacity()

        assert "capacity_overview" in result
        assert "compliance_summary" in result
        assert result["capacity_overview"]["total"] == 1
        assert result["compliance_summary"]["total"] == 1


# ---------------------------------------------------------------------------
# TestPolicyExceptions (C32)
# ---------------------------------------------------------------------------


class TestPolicyExceptions:
    def _session_with_boxes_and_contents(self, boxes, contents_map=None):
        """Session whose query(BoxItem).all() returns boxes and list_contents is routed via contents_map."""
        session = _mock_session()
        _contents_map = contents_map or {}

        def mock_query(model):
            q = MagicMock()
            if model is BoxItem:
                q.all.return_value = boxes
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is BoxContent:
                def content_filter(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = []
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = content_filter
                q.order_by.return_value = q
                q.all.return_value = []
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        def get_side_effect(model, pk):
            if model is BoxItem:
                return next((b for b in boxes if b.id == pk), None)
            return None

        session.get.side_effect = get_side_effect

        return session

    def test_policy_overview(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.barcode = "BC001"
        b1.material = "cardboard"
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0
        b1.cost = 2.5

        b2 = _make_box(box_id="b2", state="draft")
        b2.barcode = None
        b2.material = None
        b2.width = None
        b2.height = None
        b2.depth = None
        b2.cost = None

        b3 = _make_box(box_id="b3", state="active")
        b3.barcode = "BC003"
        b3.material = "wood"
        b3.width = 200.0
        b3.height = 150.0
        b3.depth = 100.0
        b3.cost = 5.0

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.policy_overview()

        assert result["total"] == 3
        assert result["with_barcode"] == 2
        assert result["with_material"] == 2
        assert result["with_dimensions"] == 2
        assert result["with_cost"] == 2
        assert result["fully_compliant"] == 2
        # 2/3 * 100 = 66.7
        assert result["policy_compliance_pct"] == 66.7

    def test_policy_overview_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.policy_overview()

        assert result["total"] == 0
        assert result["with_barcode"] == 0
        assert result["with_material"] == 0
        assert result["with_dimensions"] == 0
        assert result["with_cost"] == 0
        assert result["fully_compliant"] == 0
        assert result["policy_compliance_pct"] is None

    def test_exceptions_summary(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.barcode = "BC001"
        b1.material = "cardboard"
        b1.cost = 2.5

        b2 = _make_box(box_id="b2", state="draft")
        b2.barcode = None
        b2.material = None
        b2.cost = None

        b3 = _make_box(box_id="b3", state="archived")
        b3.barcode = "BC003"
        b3.material = "wood"
        b3.cost = 5.0

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.exceptions_summary()

        assert "b2" in result["missing_barcode"]
        assert "b2" in result["missing_material"]
        assert "b2" in result["missing_cost"]
        assert len(result["missing_barcode"]) == 1
        assert len(result["missing_material"]) == 1
        assert len(result["missing_cost"]) == 1
        assert result["archived_active_contents"] == []  # no contents mocked
        assert result["over_max_quantity"] == []
        assert result["total_exceptions"] == 3

    def test_exceptions_summary_clean(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.barcode = "BC001"
        b1.material = "cardboard"
        b1.cost = 2.5

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.exceptions_summary()

        assert result["missing_barcode"] == []
        assert result["missing_material"] == []
        assert result["missing_cost"] == []
        assert result["archived_active_contents"] == []
        assert result["over_max_quantity"] == []
        assert result["total_exceptions"] == 0

    def test_box_policy_check_compliant(self):
        session = _mock_session()
        box = _make_box(state="active")
        box.barcode = "BC001"
        box.material = "cardboard"
        box.width = 100.0
        box.height = 80.0
        box.depth = 50.0
        box.cost = 2.5
        box.tare_weight = 0.5
        session.get.return_value = box

        service = BoxService(session)
        result = service.box_policy_check("box-1")

        assert result["box_id"] == "box-1"
        assert result["has_barcode"] is True
        assert result["has_material"] is True
        assert result["has_dimensions"] is True
        assert result["has_cost"] is True
        assert result["has_weight"] is True
        assert result["is_compliant"] is True
        assert result["exceptions"] == []

    def test_box_policy_check_incomplete(self):
        session = _mock_session()
        box = _make_box(state="draft")
        box.barcode = None
        box.material = None
        box.width = None
        box.height = None
        box.depth = None
        box.cost = None
        box.tare_weight = None
        session.get.return_value = box

        service = BoxService(session)
        result = service.box_policy_check("box-1")

        assert result["has_barcode"] is False
        assert result["has_material"] is False
        assert result["has_dimensions"] is False
        assert result["has_cost"] is False
        assert result["has_weight"] is False
        assert result["is_compliant"] is False
        assert "missing_barcode" in result["exceptions"]
        assert "missing_material" in result["exceptions"]
        assert "missing_dimensions" in result["exceptions"]
        assert "missing_cost" in result["exceptions"]
        assert "missing_weight" in result["exceptions"]
        assert len(result["exceptions"]) == 5

    def test_box_policy_check_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.box_policy_check("nonexistent")

    def test_export_exceptions(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.barcode = "BC001"
        b1.material = "cardboard"
        b1.width = 100.0
        b1.height = 80.0
        b1.depth = 50.0
        b1.cost = 2.5

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.export_exceptions()

        assert "policy_overview" in result
        assert "exceptions_summary" in result
        assert result["policy_overview"]["total"] == 1
        assert result["exceptions_summary"]["total_exceptions"] == 0


# ---------------------------------------------------------------------------
# TestReservationsTraceability (C35)
# ---------------------------------------------------------------------------


class TestReservationsTraceability:
    def _session_with_boxes_and_contents(self, boxes, contents_map=None):
        """Session whose query(BoxItem).all() returns boxes and list_contents is routed via contents_map."""
        session = _mock_session()
        _contents_map = contents_map or {}

        def mock_query(model):
            q = MagicMock()
            if model is BoxItem:
                q.all.return_value = boxes
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is BoxContent:
                def content_filter(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = []
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = content_filter
                q.order_by.return_value = q
                q.all.return_value = []
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        def get_side_effect(model, pk):
            if model is BoxItem:
                return next((b for b in boxes if b.id == pk), None)
            return None

        session.get.side_effect = get_side_effect

        return session

    def test_reservations_overview(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.max_quantity = 10

        b2 = _make_box(box_id="b2", state="draft")
        b2.max_quantity = 5

        b3 = _make_box(box_id="b3", state="active")
        b3.max_quantity = None

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.reservations_overview()

        assert result["total"] == 3
        assert result["by_state"]["active"] == 2
        assert result["by_state"]["draft"] == 1
        # No contents mocked -> all unreserved
        assert result["reserved"] == 0
        assert result["unreserved"] == 3
        assert result["average_fill_rate"] == 0.0

    def test_reservations_overview_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.reservations_overview()

        assert result["total"] == 0
        assert result["by_state"] == {}
        assert result["reserved"] == 0
        assert result["unreserved"] == 0
        assert result["average_fill_rate"] == 0.0

    def test_traceability_summary(self):
        # No contents mocked -> all zeroes
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="draft")

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)
        result = service.traceability_summary()

        assert result["total_contents"] == 0
        assert result["with_lot_serial"] == 0
        assert result["without_lot_serial"] == 0
        assert result["boxes_with_traceability"] == 0
        assert result["boxes_without_traceability"] == 0
        assert result["traceability_pct"] == 0.0

    def test_traceability_summary_no_lots(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.traceability_summary()

        assert result["total_contents"] == 0
        assert result["with_lot_serial"] == 0
        assert result["without_lot_serial"] == 0
        assert result["traceability_pct"] == 0.0

    def test_box_reservations(self):
        session = _mock_session()
        box = _make_box(state="active")
        box.max_quantity = 10
        session.get.return_value = box

        c1 = MagicMock(spec=BoxContent)
        c1.id = "c-1"
        c1.item_id = "item-1"
        c1.quantity = 5.0
        c1.lot_serial = "LOT-001"
        c1.note = None
        c2 = MagicMock(spec=BoxContent)
        c2.id = "c-2"
        c2.item_id = "item-2"
        c2.quantity = 3.0
        c2.lot_serial = None
        c2.note = "test note"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1, c2]

        service = BoxService(session)
        result = service.box_reservations("box-1")

        assert result["box_id"] == "box-1"
        assert result["box_name"] == "Test Box"
        assert result["state"] == "active"
        assert result["contents_count"] == 2
        assert result["max_quantity"] == 10
        assert result["fill_pct"] == 20.0
        assert result["lot_serial_count"] == 1
        assert result["lot_serial_pct"] == 50.0
        assert len(result["contents"]) == 2
        assert result["contents"][0]["lot_serial"] == "LOT-001"
        assert result["contents"][1]["lot_serial"] is None

    def test_box_reservations_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.box_reservations("nonexistent")

    def test_export_traceability(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.max_quantity = 10

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.export_traceability()

        assert "reservations_overview" in result
        assert "traceability_summary" in result
        assert "per_box_details" in result
        assert result["reservations_overview"]["total"] == 1
        assert result["traceability_summary"]["total_contents"] == 0
        # No contents mocked -> per_box_details is empty (only boxes with contents included)
        assert result["per_box_details"] == []

    def test_export_traceability_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.export_traceability()

        assert "reservations_overview" in result
        assert "traceability_summary" in result
        assert "per_box_details" in result
        assert result["reservations_overview"]["total"] == 0
        assert result["traceability_summary"]["total_contents"] == 0
        assert result["per_box_details"] == []


# ---------------------------------------------------------------------------
# TestAllocationsCustody (C38)
# ---------------------------------------------------------------------------


class TestAllocationsCustody:
    def _session_with_boxes_and_contents(self, boxes, contents_map=None):
        """Session whose query(BoxItem).all() returns boxes and list_contents is routed via contents_map."""
        session = _mock_session()
        _contents_map = contents_map or {}

        def mock_query(model):
            q = MagicMock()
            if model is BoxItem:
                q.all.return_value = boxes
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is BoxContent:
                def content_filter(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = []
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = content_filter
                q.order_by.return_value = q
                q.all.return_value = []
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        def get_side_effect(model, pk):
            if model is BoxItem:
                return next((b for b in boxes if b.id == pk), None)
            return None

        session.get.side_effect = get_side_effect

        return session

    def test_allocations_overview(self):
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="draft")
        b3 = _make_box(box_id="b3", state="active")

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.allocations_overview()

        assert result["total"] == 3
        # No contents mocked -> all unallocated
        assert result["allocated"] == 0
        assert result["unallocated"] == 3
        assert result["allocation_rate"] == 0.0
        assert result["by_state"]["active"] == 2
        assert result["by_state"]["draft"] == 1

    def test_allocations_overview_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.allocations_overview()

        assert result["total"] == 0
        assert result["allocated"] == 0
        assert result["unallocated"] == 0
        assert result["allocation_rate"] == 0.0
        assert result["by_state"] == {}

    def test_custody_summary(self):
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="draft")

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)
        result = service.custody_summary()

        assert result["total"] == 2
        # No contents mocked -> all zero depth
        assert result["boxes_with_contents"] == 0
        assert result["max_custody_depth"] == 0
        assert result["avg_contents_per_box"] == 0.0

    def test_custody_summary_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.custody_summary()

        assert result["total"] == 0
        assert result["boxes_with_contents"] == 0
        assert result["max_custody_depth"] == 0
        assert result["avg_contents_per_box"] == 0.0

    def test_box_custody_with_contents(self):
        session = _mock_session()
        box = _make_box(state="active")
        session.get.return_value = box

        c1 = MagicMock(spec=BoxContent)
        c1.id = "c-1"
        c1.item_id = "item-1"
        c1.quantity = 5.0
        c1.lot_serial = "LOT-001"
        c1.note = None
        c2 = MagicMock(spec=BoxContent)
        c2.id = "c-2"
        c2.item_id = "item-2"
        c2.quantity = 3.0
        c2.lot_serial = None
        c2.note = "test note"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1, c2]

        service = BoxService(session)
        result = service.box_custody("box-1")

        assert result["box_id"] == "box-1"
        assert result["box_name"] == "Test Box"
        assert result["state"] == "active"
        assert result["custody_depth"] == 2
        assert result["total_quantity"] == 8.0
        assert len(result["contents"]) == 2
        assert result["contents"][0]["item_id"] == "item-1"
        assert result["contents"][0]["lot_serial"] == "LOT-001"
        assert result["contents"][1]["item_id"] == "item-2"
        assert result["contents"][1]["lot_serial"] is None

    def test_box_custody_no_contents(self):
        session = _mock_session()
        box = _make_box(state="draft")
        session.get.return_value = box

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = []

        service = BoxService(session)
        result = service.box_custody("box-1")

        assert result["box_id"] == "box-1"
        assert result["custody_depth"] == 0
        assert result["total_quantity"] == 0.0
        assert result["contents"] == []

    def test_box_custody_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.box_custody("nonexistent")

    def test_export_custody(self):
        b1 = _make_box(box_id="b1", state="active")

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.export_custody()

        assert "allocations_overview" in result
        assert "custody_summary" in result
        assert "per_box_custody" in result
        assert result["allocations_overview"]["total"] == 1
        assert result["custody_summary"]["total"] == 1
        assert len(result["per_box_custody"]) == 1
        assert result["per_box_custody"][0]["box_id"] == "b1"

    def test_export_custody_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.export_custody()

        assert "allocations_overview" in result
        assert "custody_summary" in result
        assert "per_box_custody" in result
        assert result["allocations_overview"]["total"] == 0
        assert result["custody_summary"]["total"] == 0
        assert result["per_box_custody"] == []

    def test_allocations_overview_allocation_rate(self):
        """Verify allocation_rate calculation when all boxes are unallocated."""
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="archived")

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)
        result = service.allocations_overview()

        assert result["total"] == 2
        assert result["allocated"] == 0
        assert result["unallocated"] == 2
        assert result["allocation_rate"] == 0.0


# ---------------------------------------------------------------------------
# TestOccupancyTurnover (C41)
# ---------------------------------------------------------------------------


class TestOccupancyTurnover:
    def _session_with_boxes_and_contents(self, boxes, contents_map=None):
        """Session whose query(BoxItem).all() returns boxes and list_contents is routed via contents_map."""
        session = _mock_session()
        _contents_map = contents_map or {}

        def mock_query(model):
            q = MagicMock()
            if model is BoxItem:
                q.all.return_value = boxes
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is BoxContent:
                def content_filter(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = []
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = content_filter
                q.order_by.return_value = q
                q.all.return_value = []
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        def get_side_effect(model, pk):
            if model is BoxItem:
                return next((b for b in boxes if b.id == pk), None)
            return None

        session.get.side_effect = get_side_effect

        return session

    def test_occupancy_overview(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.max_quantity = 10
        b2 = _make_box(box_id="b2", state="draft")
        b2.max_quantity = 5
        b3 = _make_box(box_id="b3", state="active")
        b3.max_quantity = None

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.occupancy_overview()

        assert result["total"] == 3
        # No contents mocked -> all empty
        assert result["occupied"] == 0
        assert result["empty"] == 3
        assert result["occupancy_rate"] == 0.0
        assert result["avg_fill_level"] == 0.0

    def test_occupancy_overview_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.occupancy_overview()

        assert result["total"] == 0
        assert result["occupied"] == 0
        assert result["empty"] == 0
        assert result["occupancy_rate"] == 0.0
        assert result["avg_fill_level"] == 0.0

    def test_occupancy_overview_all_empty_boxes(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.max_quantity = 10
        b2 = _make_box(box_id="b2", state="active")
        b2.max_quantity = 20

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)
        result = service.occupancy_overview()

        assert result["total"] == 2
        assert result["occupied"] == 0
        assert result["empty"] == 2
        assert result["occupancy_rate"] == 0.0
        assert result["avg_fill_level"] == 0.0

    def test_turnover_summary(self):
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="draft")
        b3 = _make_box(box_id="b3", state="active")

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.turnover_summary()

        assert result["total"] == 3
        assert result["active_boxes"] == 2
        # No contents mocked -> avg 0, all active boxes have 0 contents -> low turnover
        assert result["avg_contents_per_active"] == 0.0
        assert result["high_turnover"] == 0
        assert result["low_turnover"] == 2

    def test_turnover_summary_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.turnover_summary()

        assert result["total"] == 0
        assert result["active_boxes"] == 0
        assert result["avg_contents_per_active"] == 0.0
        assert result["high_turnover"] == 0
        assert result["low_turnover"] == 0

    def test_box_turnover_with_contents(self):
        session = _mock_session()
        box = _make_box(state="active")
        box.max_quantity = 10
        session.get.return_value = box

        c1 = MagicMock(spec=BoxContent)
        c1.quantity = 5.0
        c2 = MagicMock(spec=BoxContent)
        c2.quantity = 3.0

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1, c2]

        service = BoxService(session)
        result = service.box_turnover("box-1")

        assert result["box_id"] == "box-1"
        assert result["box_name"] == "Test Box"
        assert result["state"] == "active"
        assert result["contents_count"] == 2
        assert result["max_quantity"] == 10
        assert result["fill_ratio"] == 20.0
        assert result["classification"] == "normal"

    def test_box_turnover_no_contents(self):
        session = _mock_session()
        box = _make_box(state="draft")
        box.max_quantity = None
        session.get.return_value = box

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = []

        service = BoxService(session)
        result = service.box_turnover("box-1")

        assert result["box_id"] == "box-1"
        assert result["contents_count"] == 0
        assert result["fill_ratio"] == 0.0
        assert result["classification"] == "low"

    def test_box_turnover_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.box_turnover("nonexistent")

    def test_export_turnover(self):
        b1 = _make_box(box_id="b1", state="active")
        b1.max_quantity = 10

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.export_turnover()

        assert "occupancy_overview" in result
        assert "turnover_summary" in result
        assert "per_box_turnover" in result
        assert result["occupancy_overview"]["total"] == 1
        assert result["turnover_summary"]["total"] == 1
        assert len(result["per_box_turnover"]) == 1
        assert result["per_box_turnover"][0]["box_id"] == "b1"

    def test_export_turnover_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.export_turnover()

        assert "occupancy_overview" in result
        assert "turnover_summary" in result
        assert "per_box_turnover" in result
        assert result["occupancy_overview"]["total"] == 0
        assert result["turnover_summary"]["total"] == 0
        assert result["per_box_turnover"] == []


# ---------------------------------------------------------------------------
# TestDwellAging (C44)
# ---------------------------------------------------------------------------


class TestDwellAging:
    def _session_with_boxes_and_contents(self, boxes, contents_map=None):
        """Session whose query(BoxItem).all() returns boxes and list_contents is routed via contents_map."""
        session = _mock_session()
        _contents_map = contents_map or {}

        def mock_query(model):
            q = MagicMock()
            if model is BoxItem:
                q.all.return_value = boxes
                q.filter.return_value = q
                q.order_by.return_value = q
            elif model is BoxContent:
                def content_filter(*args, **kwargs):
                    fq = MagicMock()
                    fq.all.return_value = []
                    fq.order_by.return_value = fq
                    return fq

                q.filter.side_effect = content_filter
                q.order_by.return_value = q
                q.all.return_value = []
            else:
                q.all.return_value = []
                q.filter.return_value = q
                q.order_by.return_value = q
            return q

        session.query.side_effect = mock_query

        def get_side_effect(model, pk):
            if model is BoxItem:
                return next((b for b in boxes if b.id == pk), None)
            return None

        session.get.side_effect = get_side_effect

        return session

    # -- dwell_overview --

    def test_dwell_overview(self):
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="draft")
        b3 = _make_box(box_id="b3", state="active")

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.dwell_overview()

        assert result["total"] == 3
        # No contents mocked -> all have 0 items -> all low_dwell
        assert result["avg_items_per_box"] == 0.0
        assert result["high_dwell"] == 0
        assert result["high_dwell_ids"] == []
        assert result["low_dwell"] == 3
        assert set(result["low_dwell_ids"]) == {"b1", "b2", "b3"}

    def test_dwell_overview_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.dwell_overview()

        assert result["total"] == 0
        assert result["avg_items_per_box"] == 0.0
        assert result["high_dwell"] == 0
        assert result["low_dwell"] == 0

    def test_dwell_overview_high_and_low(self):
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="active")

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)

        # Patch list_contents to return different counts per box
        contents_b1 = [MagicMock(spec=BoxContent, quantity=1.0) for _ in range(12)]
        contents_b2 = [MagicMock(spec=BoxContent, quantity=1.0)]

        def mock_list_contents(box_id):
            if box_id == "b1":
                return contents_b1
            elif box_id == "b2":
                return contents_b2
            return []

        service.list_contents = mock_list_contents
        result = service.dwell_overview()

        assert result["total"] == 2
        assert result["high_dwell"] == 1
        assert result["low_dwell"] == 1

    # -- aging_summary --

    def test_aging_summary(self):
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="draft")

        session = self._session_with_boxes_and_contents([b1, b2])
        service = BoxService(session)
        result = service.aging_summary()

        assert result["total"] == 2
        # No contents mocked -> all fresh (0 items)
        assert result["mature"] == 0
        assert result["active"] == 0
        assert result["fresh"] == 2
        assert set(result["fresh_ids"]) == {"b1", "b2"}

    def test_aging_summary_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.aging_summary()

        assert result["total"] == 0
        assert result["mature"] == 0
        assert result["active"] == 0
        assert result["fresh"] == 0

    def test_aging_summary_all_tiers(self):
        b1 = _make_box(box_id="b1", state="active")
        b2 = _make_box(box_id="b2", state="active")
        b3 = _make_box(box_id="b3", state="active")

        session = self._session_with_boxes_and_contents([b1, b2, b3])
        service = BoxService(session)
        result = service.aging_summary()

        # All have 0 contents -> all fresh
        assert result["total"] == 3
        assert result["fresh"] == 3
        assert result["mature"] == 0
        assert result["active"] == 0

    # -- box_aging --

    def test_box_aging_with_items(self):
        session = _mock_session()
        box = _make_box(state="active")
        session.get.return_value = box

        c1 = MagicMock(spec=BoxContent)
        c1.id = "c1"
        c1.item_id = "item-1"
        c1.quantity = 5.0
        c1.lot_serial = "LOT-001"
        c1.note = None
        c2 = MagicMock(spec=BoxContent)
        c2.id = "c2"
        c2.item_id = "item-2"
        c2.quantity = 3.0
        c2.lot_serial = None
        c2.note = "test"

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = [c1, c2]

        service = BoxService(session)
        result = service.box_aging("box-1")

        assert result["box_id"] == "box-1"
        assert result["box_name"] == "Test Box"
        assert result["state"] == "active"
        assert result["item_count"] == 2
        assert result["age_tier"] == "fresh"
        assert result["total_quantity"] == 8.0
        assert len(result["contents"]) == 2

    def test_box_aging_no_items(self):
        session = _mock_session()
        box = _make_box(state="draft")
        session.get.return_value = box

        query_mock = MagicMock()
        session.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = []

        service = BoxService(session)
        result = service.box_aging("box-1")

        assert result["box_id"] == "box-1"
        assert result["item_count"] == 0
        assert result["age_tier"] == "fresh"
        assert result["total_quantity"] == 0.0
        assert result["contents"] == []

    def test_box_aging_not_found(self):
        session = _mock_session()
        session.get.return_value = None

        service = BoxService(session)
        with pytest.raises(ValueError, match="not found"):
            service.box_aging("nonexistent")

    # -- export_aging --

    def test_export_aging(self):
        b1 = _make_box(box_id="b1", state="active")

        session = self._session_with_boxes_and_contents([b1])
        service = BoxService(session)
        result = service.export_aging()

        assert "dwell_overview" in result
        assert "aging_summary" in result
        assert "per_box_aging" in result
        assert result["dwell_overview"]["total"] == 1
        assert result["aging_summary"]["total"] == 1
        assert len(result["per_box_aging"]) == 1
        assert result["per_box_aging"][0]["box_id"] == "b1"

    def test_export_aging_empty(self):
        session = self._session_with_boxes_and_contents([])
        service = BoxService(session)
        result = service.export_aging()

        assert "dwell_overview" in result
        assert "aging_summary" in result
        assert "per_box_aging" in result
        assert result["dwell_overview"]["total"] == 0
        assert result["aging_summary"]["total"] == 0
        assert result["per_box_aging"] == []
