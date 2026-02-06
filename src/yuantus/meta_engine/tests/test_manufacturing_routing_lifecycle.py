from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.models import Operation, Routing, WorkCenter
from yuantus.meta_engine.manufacturing.routing_service import RoutingService


def _operation_list_query(items):
    query = MagicMock()
    filtered = MagicMock()
    filtered.order_by.return_value = filtered
    filtered.all.return_value = list(items)
    filtered.first.return_value = items[0] if items else None
    query.filter.return_value = filtered
    return query


def test_update_operation_applies_fields_and_workcenter_resolution():
    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", version="1.0")
    operation = Operation(
        id="op-1",
        routing_id="routing-1",
        operation_number="10",
        name="Cut",
        operation_type="fabrication",
        sequence=10,
        run_time=1.0,
    )
    workcenter = WorkCenter(id="wc-1", code="WC-1", name="WC", is_active=True)

    def _get(model, key):
        if model == Routing:
            return routing
        if model == WorkCenter and key == "wc-1":
            return workcenter
        return None

    session.get.side_effect = _get
    session.query.side_effect = lambda model: _operation_list_query([operation])

    service = RoutingService(session)
    service._update_routing_totals = MagicMock()

    updated = service.update_operation(
        "routing-1",
        "op-1",
        {
            "name": "Cut Updated",
            "run_time": 2.5,
            "workcenter_id": "wc-1",
        },
    )

    assert updated.name == "Cut Updated"
    assert updated.run_time == pytest.approx(2.5)
    assert updated.workcenter_id == "wc-1"
    assert updated.workcenter_code == "WC-1"
    assert service._update_routing_totals.called


def test_delete_operation_resequences_and_recalculates():
    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", version="1.0")
    operation = Operation(id="op-1", routing_id="routing-1", operation_number="10", name="Cut")

    session.get.side_effect = lambda model, key: routing if model == Routing else None
    query = MagicMock()
    filtered = MagicMock()
    filtered.first.return_value = operation
    query.filter.return_value = filtered
    session.query.side_effect = lambda model: query

    service = RoutingService(session)
    service._resequence_existing_operations = MagicMock(return_value=[])
    service._update_routing_totals = MagicMock()

    service.delete_operation("routing-1", "op-1")

    assert session.delete.called
    assert service._resequence_existing_operations.called
    assert service._update_routing_totals.called


def test_resequence_operations_rejects_duplicates():
    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", version="1.0")
    session.get.side_effect = lambda model, key: routing if model == Routing else None
    service = RoutingService(session)

    with pytest.raises(ValueError, match="contains duplicates"):
        service.resequence_operations(
            "routing-1",
            ["op-1", "op-1"],
            step=10,
        )


def test_resequence_operations_applies_requested_order():
    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", version="1.0")
    op1 = Operation(id="op-1", routing_id="routing-1", operation_number="10", name="Cut", sequence=10)
    op2 = Operation(id="op-2", routing_id="routing-1", operation_number="20", name="Weld", sequence=20)
    op3 = Operation(id="op-3", routing_id="routing-1", operation_number="30", name="Inspect", sequence=30)

    session.get.side_effect = lambda model, key: routing if model == Routing else None
    session.query.side_effect = lambda model: _operation_list_query([op1, op2, op3])

    service = RoutingService(session)
    result = service.resequence_operations(
        "routing-1",
        ["op-3", "op-1", "op-2"],
        step=5,
    )

    assert [operation.id for operation in result] == ["op-3", "op-1", "op-2"]
    assert op3.sequence == 5
    assert op1.sequence == 10
    assert op2.sequence == 15


def test_release_routing_validates_primary_count():
    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", version="1.0", state="draft")

    session.get.side_effect = lambda model, key: routing if model == Routing else None
    service = RoutingService(session)
    service.list_operations = MagicMock(
        return_value=[Operation(id="op-1", routing_id="routing-1", operation_number="10", name="Cut")]
    )

    routing_query = MagicMock()
    routing_filtered = MagicMock()
    routing_filtered.count.return_value = 2
    routing_query.filter.return_value = routing_filtered
    session.query.side_effect = lambda model: routing_query

    with pytest.raises(ValueError, match="exactly one primary"):
        service.release_routing("routing-1")


def test_release_and_reopen_routing_success():
    session = MagicMock()
    routing = Routing(id="routing-1", item_id="item-1", name="R1", version="1.0", state="draft")
    operation = Operation(
        id="op-1",
        routing_id="routing-1",
        operation_number="10",
        name="Cut",
        workcenter_id="wc-1",
        workcenter_code="WC-1",
    )

    def _get(model, key):
        if model == Routing and key == "routing-1":
            return routing
        return None

    session.get.side_effect = _get

    routing_query = MagicMock()
    routing_filtered = MagicMock()
    routing_filtered.count.return_value = 1
    routing_query.filter.return_value = routing_filtered
    session.query.side_effect = lambda model: routing_query

    service = RoutingService(session)
    service.list_operations = MagicMock(return_value=[operation])
    service._resolve_workcenter = MagicMock(return_value=("wc-1", "WC-1"))

    released = service.release_routing("routing-1")
    assert released.state == "released"

    reopened = service.reopen_routing("routing-1")
    assert reopened.state == "draft"
