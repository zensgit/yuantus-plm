from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.models import Routing
from yuantus.meta_engine.manufacturing.routing_service import RoutingService


def _routing_query(items):
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.all.return_value = list(items)
    return query


def test_create_routing_primary_clears_existing_primary_in_scope():
    session = MagicMock()
    existing_primary = Routing(
        id="routing-old",
        item_id="item-1",
        name="Old Primary",
        version="1.0",
        is_primary=True,
    )
    session.query.side_effect = lambda model: _routing_query([existing_primary])

    service = RoutingService(session)
    created = service.create_routing(
        "Routing New",
        item_id="item-1",
        is_primary=True,
    )

    assert created.is_primary is True
    assert existing_primary.is_primary is False
    assert session.flush.called


def test_set_primary_routing_switches_primary_within_scope():
    session = MagicMock()
    target = Routing(
        id="routing-target",
        item_id="item-1",
        name="Target",
        version="1.0",
        is_primary=False,
    )
    old_primary = Routing(
        id="routing-old",
        item_id="item-1",
        name="Old",
        version="1.0",
        is_primary=True,
    )
    session.get.side_effect = lambda model, rid: target if model == Routing and rid == "routing-target" else None
    session.query.side_effect = lambda model: _routing_query([old_primary])

    service = RoutingService(session)
    updated = service.set_primary_routing("routing-target")

    assert updated.id == "routing-target"
    assert updated.is_primary is True
    assert old_primary.is_primary is False
    assert session.flush.called


def test_set_primary_routing_rejects_missing_scope():
    session = MagicMock()
    target = Routing(
        id="routing-target",
        item_id=None,
        mbom_id=None,
        name="Target",
        version="1.0",
        is_primary=False,
    )
    session.get.side_effect = lambda model, rid: target if model == Routing and rid == "routing-target" else None
    service = RoutingService(session)

    with pytest.raises(ValueError, match="missing scope"):
        service.set_primary_routing("routing-target")


def test_set_primary_routing_not_found():
    session = MagicMock()
    session.get.return_value = None
    service = RoutingService(session)

    with pytest.raises(ValueError, match="Routing not found: routing-missing"):
        service.set_primary_routing("routing-missing")
