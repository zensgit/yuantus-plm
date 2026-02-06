from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.models import Operation, Routing, WorkCenter
from yuantus.meta_engine.manufacturing.routing_service import RoutingService


def _build_operation_query(count: int = 0):
    query = MagicMock()
    filtered = MagicMock()
    filtered.count.return_value = count
    filtered.all.return_value = []
    filtered.order_by.return_value = filtered
    query.filter.return_value = filtered
    return query


def test_add_operation_rejects_unknown_workcenter_code():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")

    workcenter_query = MagicMock()
    workcenter_filtered = MagicMock()
    workcenter_filtered.first.return_value = None
    workcenter_query.filter.return_value = workcenter_filtered

    session.get.side_effect = lambda model, item_id: routing if model == Routing else None
    session.query.side_effect = (
        lambda model: _build_operation_query(0) if model == Operation else workcenter_query
    )

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

    workcenter_query = MagicMock()
    workcenter_filtered = MagicMock()
    workcenter_filtered.first.return_value = inactive_wc
    workcenter_query.filter.return_value = workcenter_filtered

    session.get.side_effect = lambda model, item_id: routing if model == Routing else None
    session.query.side_effect = (
        lambda model: _build_operation_query(0) if model == Operation else workcenter_query
    )

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    with pytest.raises(ValueError, match="WorkCenter is inactive: WC-INACTIVE"):
        service.add_operation(
            "routing-1",
            "10",
            "Cut",
            workcenter_code="WC-INACTIVE",
        )


def test_add_operation_accepts_active_workcenter_code_and_sets_id():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")
    active_wc = WorkCenter(id="wc-1", code="WC-ACTIVE", name="Active", is_active=True)

    workcenter_query = MagicMock()
    workcenter_filtered = MagicMock()
    workcenter_filtered.first.return_value = active_wc
    workcenter_query.filter.return_value = workcenter_filtered

    session.get.side_effect = lambda model, item_id: routing if model == Routing else None
    session.query.side_effect = (
        lambda model: _build_operation_query(0) if model == Operation else workcenter_query
    )

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    op = service.add_operation(
        "routing-1",
        "10",
        "Cut",
        workcenter_code="  WC-ACTIVE  ",
    )

    assert op.workcenter_id == "wc-1"
    assert op.workcenter_code == "WC-ACTIVE"
    assert session.add.called
    assert session.flush.called


def test_add_operation_accepts_workcenter_id_and_ignores_missing_code_lookup():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")
    active_wc = WorkCenter(id="wc-9", code="WC-ID", name="ById", is_active=True)

    def _get(model, item_id):
        if model == Routing:
            return routing
        if model == WorkCenter and item_id == "wc-9":
            return active_wc
        return None

    session.get.side_effect = _get
    session.query.side_effect = lambda model: _build_operation_query(0)

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    op = service.add_operation(
        "routing-1",
        "10",
        "Cut",
        workcenter_id="wc-9",
    )

    assert op.workcenter_id == "wc-9"
    assert op.workcenter_code == "WC-ID"


def test_add_operation_rejects_id_code_mismatch():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")
    active_wc = WorkCenter(id="wc-9", code="WC-ID", name="ById", is_active=True)

    def _get(model, item_id):
        if model == Routing:
            return routing
        if model == WorkCenter and item_id == "wc-9":
            return active_wc
        return None

    session.get.side_effect = _get
    session.query.side_effect = lambda model: _build_operation_query(0)

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    with pytest.raises(ValueError, match="WorkCenter id/code mismatch"):
        service.add_operation(
            "routing-1",
            "10",
            "Cut",
            workcenter_id="wc-9",
            workcenter_code="WC-OTHER",
        )


def test_add_operation_rejects_unknown_workcenter_id():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")

    session.get.side_effect = lambda model, item_id: routing if model == Routing else None
    session.query.side_effect = lambda model: _build_operation_query(0)

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    with pytest.raises(ValueError, match="WorkCenter not found: wc-missing"):
        service.add_operation(
            "routing-1",
            "10",
            "Cut",
            workcenter_id="wc-missing",
        )


def test_add_operation_rejects_inactive_workcenter_id():
    session = MagicMock()
    routing = Routing(id="routing-1", name="R1")
    inactive_wc = WorkCenter(id="wc-1", code="WC-INACTIVE", name="Inactive", is_active=False)

    def _get(model, item_id):
        if model == Routing:
            return routing
        if model == WorkCenter and item_id == "wc-1":
            return inactive_wc
        return None

    session.get.side_effect = _get
    session.query.side_effect = lambda model: _build_operation_query(0)

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    with pytest.raises(ValueError, match="WorkCenter is inactive: WC-INACTIVE"):
        service.add_operation(
            "routing-1",
            "10",
            "Cut",
            workcenter_id="wc-1",
        )


def test_copy_routing_preserves_workcenter_id_and_code():
    session = MagicMock()
    source = Routing(id="routing-src", name="Source", version="1.0", mbom_id=None, item_id="item-1")
    source_op = Operation(
        id="op-src",
        routing_id="routing-src",
        operation_number="10",
        name="Cut",
        operation_type="fabrication",
        sequence=10,
        workcenter_id="wc-1",
        workcenter_code="WC-1",
    )

    session.get.side_effect = lambda model, item_id: source if model == Routing else None
    query = MagicMock()
    filtered = MagicMock()
    filtered.order_by.return_value = filtered
    filtered.all.return_value = [source_op]
    query.filter.return_value = filtered
    session.query.side_effect = lambda model: query if model == Operation else MagicMock()

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    created = []
    def capture_add(obj):
        created.append(obj)
    session.add.side_effect = capture_add

    new_routing = service.copy_routing("routing-src", "Copy")
    new_ops = [obj for obj in created if isinstance(obj, Operation) and obj.routing_id == new_routing.id]
    assert len(new_ops) == 1
    assert new_ops[0].workcenter_id == "wc-1"
    assert new_ops[0].workcenter_code == "WC-1"
