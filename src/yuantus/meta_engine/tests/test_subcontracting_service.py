"""Tests for C13 – Subcontracting bootstrap service layer."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.models import Operation
from yuantus.meta_engine.subcontracting.models import SubcontractOrder, SubcontractOrderEvent
from yuantus.meta_engine.subcontracting.service import SubcontractingService


class _MockQuery:
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
    store = {}

    def mock_add(obj):
        store[obj.id] = obj

    def mock_get(model, obj_id):
        obj = store.get(obj_id)
        if obj and isinstance(obj, model):
            return obj
        return None

    def mock_flush():
        pass

    def mock_query(model):
        return _MockQuery(obj for obj in store.values() if isinstance(obj, model))

    session.add.side_effect = mock_add
    session.get.side_effect = mock_get
    session.flush.side_effect = mock_flush
    session.query.side_effect = mock_query
    session._store = store
    return session


def test_create_order_with_operation_context_prefills_vendor_and_routing():
    session = _mock_session()
    op = Operation(
        id="op-1",
        routing_id="routing-1",
        operation_number="20",
        name="Outside coating",
        is_subcontracted=True,
        subcontractor_id="vendor-1",
    )
    session.add(op)
    svc = SubcontractingService(session)

    order = svc.create_order(
        name="Subcontract coating",
        requested_qty=10,
        source_operation_id="op-1",
    )

    assert order.routing_id == "routing-1"
    assert order.vendor_id == "vendor-1"
    assert order.state == "draft"


def test_assign_vendor_updates_read_model():
    session = _mock_session()
    svc = SubcontractingService(session)
    order = svc.create_order(name="Heat treatment", requested_qty=5)

    svc.assign_vendor(order.id, vendor_id="vendor-22", vendor_name="Acme Heat")
    read_model = svc.get_order_read_model(order.id)

    assert read_model["vendor_id"] == "vendor-22"
    assert read_model["vendor_name"] == "Acme Heat"


def test_issue_then_receive_updates_state_and_timeline():
    session = _mock_session()
    svc = SubcontractingService(session)
    order = svc.create_order(name="Anodizing", requested_qty=8)

    issue = svc.record_material_issue(order.id, quantity=8, reference="ISS-1")
    assert issue.event_type == "material_issue"
    assert svc.get_order(order.id).state == "issued"

    receipt = svc.record_receipt(order.id, quantity=3, reference="RCV-1")
    assert receipt.event_type == "receipt"
    assert svc.get_order(order.id).state == "partially_received"

    svc.record_receipt(order.id, quantity=5, reference="RCV-2")
    assert svc.get_order(order.id).state == "completed"
    assert len(svc.get_timeline(order.id)) == 3


def test_list_orders_filters_by_vendor_and_routing():
    session = _mock_session()
    svc = SubcontractingService(session)
    first = svc.create_order(name="Vendor A", requested_qty=1, vendor_id="v-1", routing_id="r-1")
    svc.create_order(name="Vendor B", requested_qty=1, vendor_id="v-2", routing_id="r-2")

    by_vendor = svc.list_orders(vendor_id="v-1")
    by_routing = svc.list_orders(routing_id="r-1")

    assert [order.id for order in by_vendor] == [first.id]
    assert [order.id for order in by_routing] == [first.id]


def test_create_order_rejects_non_positive_requested_qty():
    session = _mock_session()
    svc = SubcontractingService(session)
    with pytest.raises(ValueError, match="requested_qty"):
        svc.create_order(name="Bad", requested_qty=0)


def test_receipt_rejects_missing_order():
    session = _mock_session()
    svc = SubcontractingService(session)
    with pytest.raises(ValueError, match="not found"):
        svc.record_receipt("missing", quantity=1)


def test_overview_analytics_totals():
    session = _mock_session()
    svc = SubcontractingService(session)
    first = svc.create_order(name="Vendor A", requested_qty=10, vendor_id="v-1")
    second = svc.create_order(name="Vendor B", requested_qty=5, vendor_id="v-2")
    svc.record_material_issue(first.id, quantity=10)
    svc.record_receipt(first.id, quantity=4)
    svc.record_receipt(second.id, quantity=5)

    overview = svc.get_overview()

    assert overview["orders_total"] == 2
    assert overview["vendors_total"] == 2
    assert overview["requested_qty_total"] == 15.0
    assert overview["received_qty_total"] == 9.0


def test_vendor_analytics_export_csv():
    session = _mock_session()
    svc = SubcontractingService(session)
    svc.create_order(name="Vendor A", requested_qty=2, vendor_id="v-1", vendor_name="Acme")
    rendered = svc.export_vendor_analytics(fmt="csv")
    assert "vendor_id,vendor_name,orders_total" in rendered
    assert "v-1,Acme,1" in rendered


def test_receipt_analytics_json_rows():
    session = _mock_session()
    svc = SubcontractingService(session)
    order = svc.create_order(name="Vendor A", requested_qty=4, vendor_id="v-1")
    svc.record_receipt(order.id, quantity=1)

    payload = svc.export_receipt_analytics(fmt="json")

    assert payload["receipts"][0]["order_id"] == order.id
    assert payload["receipts"][0]["completion_pct"] == 25.0
