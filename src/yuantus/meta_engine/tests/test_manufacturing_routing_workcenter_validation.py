from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.models import Operation, Routing, WorkCenter
from yuantus.meta_engine.manufacturing.routing_service import RoutingService


def _build_query_for_operation(count: int = 0):
    query = MagicMock()
    filtered = MagicMock()
    filtered.count.return_value = count
    filtered.all.return_value = []
    filtered.order_by.return_value = filtered
    query.filter.return_value = filtered
    return query


def _build_query_for_workcenter(item):
    query = MagicMock()
    filtered = MagicMock()
    filtered.first.return_value = item
    query.filter.return_value = filtered
    return query


def test_add_operation_rejects_unknown_workcenter_code():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")

    def _query(model):
        if model == Operation:
            return _build_query_for_operation(0)
        if model == WorkCenter:
            return _build_query_for_workcenter(None)
        raise AssertionError(f"unexpected model: {model}")

    session.get.side_effect = lambda model, item_id: routing if model == Routing else None
    session.query.side_effect = _query

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    with pytest.raises(ValueError, match="WorkCenter not found: WC-MISSING"):
        service.add_operation(
            "routing-1",
            "10",
            "Cut",
            workcenter_code="WC-MISSING",
        )


def test_add_operation_rejects_inactive_workcenter_code():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")
    inactive_wc = WorkCenter(id="wc-1", code="WC-INACTIVE", name="Inactive", is_active=False)

    def _query(model):
        if model == Operation:
            return _build_query_for_operation(0)
        if model == WorkCenter:
            return _build_query_for_workcenter(inactive_wc)
        raise AssertionError(f"unexpected model: {model}")

    session.get.side_effect = lambda model, item_id: routing if model == Routing else None
    session.query.side_effect = _query

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    with pytest.raises(ValueError, match="WorkCenter is inactive: WC-INACTIVE"):
        service.add_operation(
            "routing-1",
            "10",
            "Cut",
            workcenter_code="WC-INACTIVE",
        )


def test_add_operation_accepts_active_workcenter_code():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")
    active_wc = WorkCenter(id="wc-1", code="WC-ACTIVE", name="Active", is_active=True)

    def _query(model):
        if model == Operation:
            return _build_query_for_operation(0)
        if model == WorkCenter:
            return _build_query_for_workcenter(active_wc)
        raise AssertionError(f"unexpected model: {model}")

    session.get.side_effect = lambda model, item_id: routing if model == Routing else None
    session.query.side_effect = _query

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    op = service.add_operation(
        "routing-1",
        "10",
        "Cut",
        workcenter_code="  WC-ACTIVE  ",
    )

    assert op.workcenter_code == "WC-ACTIVE"
    assert session.add.called
    assert session.flush.called
