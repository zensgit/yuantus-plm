from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.mbom_service import MBOMService
from yuantus.meta_engine.manufacturing.models import Operation
from yuantus.meta_engine.manufacturing.routing_service import RoutingService


class FakeQuery:
    def __init__(self, items):
        self._items = items

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._items)

    def count(self):
        return len(self._items)


def test_transform_ebom_to_mbom_rules():
    session = MagicMock()
    substitute_item = MagicMock()
    substitute_item.to_dict.return_value = {
        "id": "SUB-NEW",
        "properties": {"make_buy": "buy"},
    }

    def _get(model, item_id):
        if item_id == "SUB-NEW":
            return substitute_item
        return None

    session.get.side_effect = _get

    service = MBOMService(session)

    ebom = {
        "item": {"id": "PARENT", "properties": {}},
        "children": [
            {
                "relationship": {
                    "id": "rel-phantom",
                    "properties": {"quantity": 2, "uom": "EA"},
                },
                "child": {
                    "item": {"id": "PHANTOM", "properties": {"make_buy": "phantom"}},
                    "children": [
                        {
                            "relationship": {
                                "id": "rel-grand",
                                "properties": {"quantity": 3},
                            },
                            "child": {
                                "item": {
                                    "id": "GRAND",
                                    "properties": {"scrap_rate": 0.1},
                                }
                            },
                        }
                    ],
                },
            },
            {
                "relationship": {"id": "rel-ex", "properties": {"quantity": 1}},
                "child": {"item": {"id": "EXCLUDE", "properties": {}}},
            },
            {
                "relationship": {"id": "rel-sub", "properties": {"quantity": 4}},
                "child": {"item": {"id": "SUB", "properties": {}}},
            },
        ],
    }

    rules = {
        "exclude_items": ["EXCLUDE"],
        "substitute_items": {"SUB": "SUB-NEW"},
        "collapse_phantom": True,
        "apply_scrap_rates": True,
    }

    result = service._transform_ebom_to_mbom(ebom, rules)
    children = result.get("children") or []
    child_ids = {child["item"]["id"] for child in children}

    assert session.get.called
    assert child_ids == {"GRAND", "SUB"}

    grand = next(child for child in children if child["item"]["id"] == "GRAND")
    assert grand["ebom_relationship_id"] == "rel-grand"
    assert grand.get("scrap_rate") in (None, 0, 0.0)
    assert grand["quantity"] == pytest.approx(6)

    sub = next(child for child in children if child["item"]["id"] == "SUB")
    assert sub["quantity"] == pytest.approx(4)
    assert sub["make_buy"] == "buy"


def test_routing_time_and_cost_calculation():
    ops = [
        SimpleNamespace(
            id="op-1",
            operation_number="10",
            name="Cut",
            setup_time=5,
            run_time=2,
            queue_time=1,
            move_time=1,
            labor_setup_time=4,
            labor_run_time=1,
            labor_cost_rate=60,
            overhead_rate=30,
        ),
        SimpleNamespace(
            id="op-2",
            operation_number="20",
            name="Assemble",
            setup_time=3,
            run_time=1,
            queue_time=0,
            move_time=0,
            labor_setup_time=2,
            labor_run_time=0.5,
            labor_cost_rate=None,
            overhead_rate=40,
        ),
    ]

    session = MagicMock()
    session.query.side_effect = lambda model: FakeQuery(ops) if model == Operation else FakeQuery([])

    service = RoutingService(session)

    time_result = service.calculate_production_time("routing-1", quantity=2)
    assert time_result["setup_time"] == pytest.approx(8)
    assert time_result["run_time"] == pytest.approx(6)
    assert time_result["queue_time"] == pytest.approx(1)
    assert time_result["move_time"] == pytest.approx(1)
    assert time_result["labor_time"] == pytest.approx(9)
    assert time_result["total_time"] == pytest.approx(16)

    cost_result = service.calculate_cost_estimate("routing-1", quantity=2)
    assert cost_result["labor_cost"] == pytest.approx(8.5)
    assert cost_result["overhead_cost"] == pytest.approx(7.83)
    assert cost_result["total_cost"] == pytest.approx(16.33)
    assert cost_result["cost_per_unit"] == pytest.approx(8.17)
