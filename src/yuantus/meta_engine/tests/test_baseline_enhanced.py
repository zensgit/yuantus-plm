from datetime import datetime
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


def test_get_comparison_details_paginates():
    session = MagicMock()
    service = BaselineService(session)
    comparison = MagicMock()
    comparison.id = "cmp-1"
    comparison.baseline_a_id = "a"
    comparison.baseline_b_id = "b"
    comparison.differences = {
        "added": [{"id": 1}, {"id": 2}],
        "removed": [{"id": 3}],
        "changed": [{"id": 4}, {"id": 5}, {"id": 6}],
    }

    session.get.return_value = comparison

    result = service.get_comparison_details(comparison_id="cmp-1", limit=2, offset=1)

    assert result["total"] == 6
    assert len(result["items"]) == 2
    assert result["items"][0]["id"] == 2


def test_get_baseline_at_date_returns_latest():
    session = MagicMock()
    service = BaselineService(session)
    baseline = Baseline(id="bl-1")

    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = baseline
    session.query.return_value = query

    result = service.get_baseline_at_date(
        root_item_id="root",
        target_date=datetime(2025, 1, 1),
        baseline_type="design",
    )

    assert result == baseline
    query.first.assert_called()


def test_list_baselines_applies_filters():
    session = MagicMock()
    service = BaselineService(session)

    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = 0
    query.all.return_value = []
    session.query.return_value = query

    service.list_baselines(
        root_item_id="root",
        root_version_id="ver",
        created_by_id=1,
        baseline_type="design",
        scope="product",
        state="released",
        effective_from=datetime(2025, 1, 1),
        effective_to=datetime(2025, 2, 1),
        limit=10,
        offset=0,
    )

    expressions = [str(call.args[0]) for call in query.filter.call_args_list]
    assert any("meta_baselines.root_item_id" in expr for expr in expressions)
    assert any("meta_baselines.root_version_id" in expr for expr in expressions)
    assert any("meta_baselines.created_by_id" in expr for expr in expressions)
    assert any("meta_baselines.baseline_type" in expr for expr in expressions)
    assert any("meta_baselines.scope" in expr for expr in expressions)
    assert any("meta_baselines.state" in expr for expr in expressions)
    assert any("meta_baselines.effective_at" in expr and ">=" in expr for expr in expressions)
    assert any("meta_baselines.effective_at" in expr and "<=" in expr for expr in expressions)


def test_export_comparison_details_supports_json_and_csv():
    session = MagicMock()
    service = BaselineService(session)

    comparison = MagicMock()
    comparison.id = "cmp-1"
    comparison.baseline_a_id = "a"
    comparison.baseline_b_id = "b"
    comparison.differences = {
        "added": [{"id": 1}],
        "removed": [{"id": 2}],
        "changed": [{"id": 3}],
    }
    session.get.return_value = comparison

    json_result = service.export_comparison_details(
        comparison_id="cmp-1",
        change_type=None,
        export_format="json",
        limit=10,
        offset=0,
    )
    assert json_result["extension"] == "json"
    assert json_result["media_type"] == "application/json"
    assert b"comparison_id" in json_result["content"]

    csv_result = service.export_comparison_details(
        comparison_id="cmp-1",
        change_type=None,
        export_format="csv",
        limit=10,
        offset=0,
    )
    assert csv_result["extension"] == "csv"
    assert csv_result["media_type"] == "text/csv"
    text = csv_result["content"].decode("utf-8-sig")
    assert "id" in text
    assert "1" in text


def test_export_comparison_details_rejects_unknown_format():
    session = MagicMock()
    service = BaselineService(session)
    comparison = MagicMock()
    comparison.id = "cmp-1"
    comparison.baseline_a_id = "a"
    comparison.baseline_b_id = "b"
    comparison.differences = {"added": [], "removed": [], "changed": []}
    session.get.return_value = comparison

    try:
        service.export_comparison_details(
            comparison_id="cmp-1",
            change_type=None,
            export_format="xlsx",
            limit=10,
            offset=0,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unsupported export format" in str(exc)
