from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.manufacturing.mbom_service import (
    MBOMService,
    _item_uom_bucket_key,
    _normalize_item_uom_bucket,
)
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


def test_item_uom_bucket_key_normalizes_uom():
    assert _item_uom_bucket_key("CHILD", " mm ") == "CHILD::MM"
    assert _item_uom_bucket_key(" CHILD ", None) == "CHILD::EA"
    assert _item_uom_bucket_key("", "EA") is None
    assert _item_uom_bucket_key(None, "EA") is None


def test_normalize_item_uom_bucket_normalizes_config_text():
    assert _normalize_item_uom_bucket(" CHILD :: mm ") == "CHILD::MM"
    assert _normalize_item_uom_bucket("CHILD") == "CHILD::EA"
    assert _normalize_item_uom_bucket("") is None
    assert _normalize_item_uom_bucket(None) is None


def test_transform_rules_exclude_item_uom_bucket_only():
    service = MBOMService(MagicMock())
    ebom = {
        "item": {"id": "PARENT", "properties": {}},
        "children": [
            {
                "relationship": {"id": "rel-ea", "properties": {"quantity": 2, "uom": "EA"}},
                "child": {"item": {"id": "CHILD", "properties": {}}},
            },
            {
                "relationship": {"id": "rel-mm", "properties": {"quantity": 3, "uom": " mm "}},
                "child": {"item": {"id": "CHILD", "properties": {}}},
            },
        ],
    }

    result = service._transform_ebom_to_mbom(
        ebom,
        {"exclude_item_uom_buckets": ["CHILD::MM"]},
    )

    children = result.get("children") or []
    assert len(children) == 1
    assert children[0]["item"]["id"] == "CHILD"
    assert children[0]["unit"] == "EA"
    assert children[0]["quantity"] == pytest.approx(2)


def test_transform_rules_substitute_item_uom_bucket_only():
    session = MagicMock()
    substitute_item = MagicMock()
    substitute_item.to_dict.return_value = {
        "id": "SUB-MM",
        "properties": {"make_buy": "buy"},
    }
    session.get.side_effect = lambda _model, item_id: (
        substitute_item if item_id == "SUB-MM" else None
    )
    service = MBOMService(session)
    ebom = {
        "item": {"id": "PARENT", "properties": {}},
        "children": [
            {
                "relationship": {"id": "rel-ea", "properties": {"quantity": 2, "uom": "EA"}},
                "child": {"item": {"id": "CHILD", "properties": {"make_buy": "make"}}},
            },
            {
                "relationship": {"id": "rel-mm", "properties": {"quantity": 3, "uom": "MM"}},
                "child": {"item": {"id": "CHILD", "properties": {"make_buy": "make"}}},
            },
        ],
    }

    result = service._transform_ebom_to_mbom(
        ebom,
        {"substitute_item_uom_buckets": {"CHILD::MM": "SUB-MM"}},
    )

    children = result.get("children") or []
    by_unit = {child["unit"]: child for child in children}
    assert by_unit["EA"]["make_buy"] == "make"
    assert by_unit["MM"]["make_buy"] == "buy"
    session.get.assert_called_once()


def test_transform_rules_normalize_configured_item_uom_bucket_text():
    service = MBOMService(MagicMock())
    ebom = {
        "item": {"id": "PARENT", "properties": {}},
        "children": [
            {
                "relationship": {"id": "rel-ea", "properties": {"quantity": 2, "uom": "EA"}},
                "child": {"item": {"id": "CHILD", "properties": {}}},
            },
            {
                "relationship": {"id": "rel-mm", "properties": {"quantity": 3, "uom": "MM"}},
                "child": {"item": {"id": "CHILD", "properties": {}}},
            },
        ],
    }

    result = service._transform_ebom_to_mbom(
        ebom,
        {"exclude_item_uom_buckets": [" CHILD :: mm "]},
    )

    children = result.get("children") or []
    assert len(children) == 1
    assert children[0]["unit"] == "EA"


def test_transform_rules_uom_bucket_substitute_overrides_legacy_substitute():
    session = MagicMock()
    sub_legacy = MagicMock()
    sub_legacy.to_dict.return_value = {
        "id": "SUB-LEGACY",
        "properties": {"make_buy": "buy"},
    }
    sub_mm = MagicMock()
    sub_mm.to_dict.return_value = {
        "id": "SUB-MM",
        "properties": {"make_buy": "buy-mm"},
    }

    def _get(_model, item_id):
        return {
            "SUB-LEGACY": sub_legacy,
            "SUB-MM": sub_mm,
        }.get(item_id)

    session.get.side_effect = _get
    service = MBOMService(session)
    ebom = {
        "item": {"id": "PARENT", "properties": {}},
        "children": [
            {
                "relationship": {"id": "rel-ea", "properties": {"quantity": 2, "uom": "EA"}},
                "child": {"item": {"id": "CHILD", "properties": {"make_buy": "make"}}},
            },
            {
                "relationship": {"id": "rel-mm", "properties": {"quantity": 3, "uom": "MM"}},
                "child": {"item": {"id": "CHILD", "properties": {"make_buy": "make"}}},
            },
        ],
    }

    result = service._transform_ebom_to_mbom(
        ebom,
        {
            "substitute_items": {"CHILD": "SUB-LEGACY"},
            "substitute_item_uom_buckets": {"CHILD::MM": "SUB-MM"},
        },
    )

    children = result.get("children") or []
    by_unit = {child["unit"]: child for child in children}
    assert by_unit["EA"]["make_buy"] == "buy"
    assert by_unit["MM"]["make_buy"] == "buy-mm"
    assert [call.args[1] for call in session.get.call_args_list] == [
        "SUB-LEGACY",
        "SUB-MM",
    ]


def test_compare_ebom_mbom_keeps_same_item_different_uom_separate():
    service = MBOMService(MagicMock())
    service.bom_service.get_bom_structure = MagicMock(
        return_value={
            "item": {"id": "ROOT", "properties": {}},
            "children": [
                {
                    "relationship": {
                        "id": "rel-ea",
                        "properties": {"quantity": 2, "uom": "EA"},
                    },
                    "child": {
                        "item": {"id": "CHILD", "properties": {}},
                        "children": [],
                    },
                },
                {
                    "relationship": {
                        "id": "rel-mm",
                        "properties": {"quantity": 100, "uom": "mm"},
                    },
                    "child": {
                        "item": {"id": "CHILD", "properties": {}},
                        "children": [],
                    },
                },
            ],
        }
    )
    service.get_mbom_structure = MagicMock(
        return_value={
            "item": {"id": "ROOT", "properties": {}},
            "children": [
                {
                    "item": {"id": "CHILD", "properties": {}},
                    "quantity": 2,
                    "unit": "EA",
                    "children": [],
                },
                {
                    "item": {"id": "CHILD", "properties": {}},
                    "quantity": 120,
                    "unit": "MM",
                    "children": [],
                },
            ],
        }
    )

    result = service.compare_ebom_mbom("ROOT", "mbom-1")

    assert result["added_in_mbom"] == []
    assert result["removed_from_ebom"] == []
    assert result["quantity_changed"] == [
        {
            "item_id": "CHILD",
            "bucket_key": "CHILD::MM",
            "uom": "MM",
            "ebom_quantity": 100,
            "mbom_quantity": 120,
        }
    ]


def test_compare_ebom_mbom_reports_uom_bucket_add_remove_not_synthetic_change():
    service = MBOMService(MagicMock())
    service.bom_service.get_bom_structure = MagicMock(
        return_value={
            "item": {"id": "ROOT", "properties": {}},
            "children": [
                {
                    "relationship": {
                        "id": "rel-ea",
                        "properties": {"quantity": 2, "uom": "EA"},
                    },
                    "child": {"item": {"id": "CHILD", "properties": {}}},
                }
            ],
        }
    )
    service.get_mbom_structure = MagicMock(
        return_value={
            "item": {"id": "ROOT", "properties": {}},
            "children": [
                {
                    "item": {"id": "CHILD", "properties": {}},
                    "quantity": 2,
                    "unit": "MM",
                }
            ],
        }
    )

    result = service.compare_ebom_mbom("ROOT", "mbom-1")

    assert result["quantity_changed"] == []
    assert result["removed_from_ebom"][0]["bucket_key"] == "CHILD::EA"
    assert result["removed_from_ebom"][0]["item_id"] == "CHILD"
    assert result["removed_from_ebom"][0]["uom"] == "EA"
    assert result["added_in_mbom"][0]["bucket_key"] == "CHILD::MM"
    assert result["added_in_mbom"][0]["item_id"] == "CHILD"
    assert result["added_in_mbom"][0]["uom"] == "MM"


def test_flatten_structure_uses_relationship_uom_and_quantity_bucket():
    service = MBOMService(MagicMock())

    result = service._flatten_structure(
        {
            "relationship": {
                "id": "rel-mm",
                "properties": {"quantity": 5, "uom": " mm "},
            },
            "child": {
                "item": {"id": "CHILD", "properties": {}},
                "children": [],
            },
        }
    )

    assert result["CHILD::MM"]["item_id"] == "CHILD"
    assert result["CHILD::MM"]["quantity"] == 5
    assert result["CHILD::MM"]["uom"] == "MM"


def test_flatten_structure_accepts_relationship_top_level_uom_and_quantity():
    service = MBOMService(MagicMock())

    result = service._flatten_structure(
        {
            "relationship": {"id": "rel-kg", "quantity": 7, "uom": "kg"},
            "child": {"item": {"id": "CHILD", "properties": {}}},
        }
    )

    assert result["CHILD::KG"]["item_id"] == "CHILD"
    assert result["CHILD::KG"]["quantity"] == 7
    assert result["CHILD::KG"]["uom"] == "KG"


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
