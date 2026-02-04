from unittest.mock import MagicMock, patch

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.bom_rollup_service import BOMRollupService


class DummyItem:
    def __init__(self) -> None:
        self.item_type_id = "Part"
        self.properties = {}


def test_compute_node_handles_missing_weights():
    service = BOMRollupService(MagicMock())
    node = {
        "id": "A",
        "item_number": "A",
        "name": "Root",
        "weight": None,
        "children": [
            {
                "relationship": {"id": "REL-1", "properties": {"quantity": 2}},
                "child": {"id": "B", "item_number": "B", "weight": "1.5"},
            },
            {
                "relationship": {"id": "REL-2", "properties": {"quantity": "bad"}},
                "child": {"id": "C", "item_number": "C", "weight": None},
            },
        ],
    }

    result = service._compute_node(node, weight_key="weight", visited=set())
    assert result["total_weight"] == 3.0
    assert result["missing_items"] == ["C"]

    child_b = next(c for c in result["children"] if c.get("item_id") == "B")
    assert child_b["quantity"] == 2.0
    assert child_b["line_weight"] == 3.0


def test_apply_write_back_overwrite_updates_properties():
    session = MagicMock()
    item = DummyItem()
    item_type = MagicMock()

    def get_side_effect(model, item_id):
        if model is Item:
            return item
        if model is ItemType:
            return item_type
        return None

    session.get.side_effect = get_side_effect
    service = BOMRollupService(session)

    rollup = {
        "item_id": "A",
        "own_weight": 1.0,
        "computed_weight": 2.0,
        "total_weight": 2.0,
        "children": [],
    }

    with patch(
        "yuantus.meta_engine.services.bom_rollup_service.get_lifecycle_state",
        return_value=None,
    ):
        updates = service._apply_write_back(
            rollup, field="weight_rollup", mode="overwrite", rounding=2
        )

    assert updates and updates[0]["status"] == "updated"
    assert item.properties["weight_rollup"] == 2.0


def test_apply_write_back_missing_skips_when_own_weight_present():
    session = MagicMock()
    service = BOMRollupService(session)

    rollup = {
        "item_id": "A",
        "own_weight": 1.0,
        "computed_weight": 2.0,
        "total_weight": 2.0,
        "children": [],
    }

    updates = service._apply_write_back(
        rollup, field="weight_rollup", mode="missing", rounding=2
    )
    assert updates == []
