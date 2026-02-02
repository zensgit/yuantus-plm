from unittest.mock import MagicMock

from yuantus.meta_engine.models.baseline import Baseline, BaselineMember
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.baseline_service import BaselineService


def test_populate_members_creates_items_and_relationships():
    session = MagicMock()
    service = BaselineService(session)

    root_item = Item(
        id="root",
        config_id="ROOT",
        generation=1,
        item_type_id="Part",
        state="released",
        properties={"revision": "A"},
    )
    child_item = Item(
        id="child",
        config_id="CHILD",
        generation=1,
        item_type_id="Part",
        state="released",
        properties={"revision": "A"},
    )

    def _get(model, key):
        if key == "root":
            return root_item
        if key == "child":
            return child_item
        return None

    session.get.side_effect = _get

    baseline = Baseline(
        id="bl-1",
        root_item_id="root",
        include_bom=True,
        include_documents=False,
        include_relationships=True,
    )

    snapshot = {
        "id": "root",
        "children": [
            {
                "relationship": {
                    "id": "rel-1",
                    "properties": {"quantity": 2},
                },
                "child": {"id": "child", "children": []},
            }
        ],
    }

    service._populate_members(baseline, snapshot)

    members = [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], BaselineMember)
    ]

    assert len(members) == 3
    member_types = {m.member_type for m in members}
    assert member_types == {"item", "relationship"}

    quantities = [m.quantity for m in members if m.item_id == "child"]
    assert quantities == ["2"]


def test_compare_baselines_detects_changes():
    session = MagicMock()
    service = BaselineService(session)

    baseline_a = Baseline(id="bl-a", name="Baseline A")
    baseline_b = Baseline(id="bl-b", name="Baseline B")

    def _get(model, key):
        if key == "bl-a":
            return baseline_a
        if key == "bl-b":
            return baseline_b
        return None

    session.get.side_effect = _get

    member_a1 = BaselineMember(
        id="m-a1",
        baseline_id="bl-a",
        item_id="item-1",
        item_number="ITEM-1",
        item_revision="A",
        item_generation=1,
        member_type="item",
    )
    member_a2 = BaselineMember(
        id="m-a2",
        baseline_id="bl-a",
        item_id="item-2",
        item_number="ITEM-2",
        item_revision="A",
        item_generation=1,
        member_type="item",
    )
    member_b1 = BaselineMember(
        id="m-b1",
        baseline_id="bl-b",
        item_id="item-1",
        item_number="ITEM-1",
        item_revision="A",
        item_generation=2,
        member_type="item",
    )
    member_b3 = BaselineMember(
        id="m-b3",
        baseline_id="bl-b",
        item_id="item-3",
        item_number="ITEM-3",
        item_revision="A",
        item_generation=1,
        member_type="item",
    )

    query_a = MagicMock()
    query_a.filter.return_value = query_a
    query_a.all.return_value = [member_a1, member_a2]

    query_b = MagicMock()
    query_b.filter.return_value = query_b
    query_b.all.return_value = [member_b1, member_b3]

    session.query.side_effect = [query_a, query_b]

    result = service.compare_baselines(
        baseline_a_id="bl-a",
        baseline_b_id="bl-b",
        user_id=1,
    )

    assert result["summary"]["added"] == 1
    assert result["summary"]["removed"] == 1
    assert result["summary"]["changed"] == 1
