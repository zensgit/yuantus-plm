from datetime import datetime
from unittest.mock import MagicMock

from yuantus.meta_engine.models.baseline import Baseline, BaselineMember
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.baseline_service import BaselineService


_MISSING = object()


def _snapshot_with_child_uom(uom=_MISSING):
    properties = {"quantity": 1}
    if uom is not _MISSING:
        properties["uom"] = uom
    return {
        "id": "root",
        "config_id": "ROOT",
        "children": [
            {
                "relationship": {
                    "id": (
                        f"rel-{str(uom).strip().lower()}"
                        if uom is not _MISSING
                        else "rel-missing"
                    ),
                    "properties": properties,
                },
                "child": {
                    "id": "item-1",
                    "config_id": "ITEM-1",
                    "generation": 1,
                    "children": [],
                },
            }
        ],
    }


def _snapshot_with_child_uom_lines(lines):
    return {
        "id": "root",
        "config_id": "ROOT",
        "children": [
            {
                "relationship": {
                    "id": relationship_id,
                    "properties": {"quantity": 1, "uom": uom},
                },
                "child": {
                    "id": "item-1",
                    "config_id": "ITEM-1",
                    "generation": 1,
                    "children": [],
                },
            }
            for relationship_id, uom in lines
        ],
    }


def _compare_baseline_pair(
    *,
    baseline_a,
    baseline_b,
    members_a,
    members_b,
):
    session = MagicMock()
    service = BaselineService(session)

    def _get(model, key):
        if key == baseline_a.id:
            return baseline_a
        if key == baseline_b.id:
            return baseline_b
        return None

    query_a = MagicMock()
    query_a.filter.return_value = query_a
    query_a.all.return_value = members_a

    query_b = MagicMock()
    query_b.filter.return_value = query_b
    query_b.all.return_value = members_b

    session.get.side_effect = _get
    session.query.side_effect = [query_a, query_b]

    return service.compare_baselines(
        baseline_a_id=baseline_a.id,
        baseline_b_id=baseline_b.id,
        user_id=1,
    )


def _child_member(*, baseline_id, generation=1, relationship_id=None, member_id=None):
    return BaselineMember(
        id=member_id or f"member-{baseline_id}",
        baseline_id=baseline_id,
        item_id="item-1",
        item_number="ITEM-1",
        item_revision="A",
        item_generation=generation,
        member_type="item",
        path="ROOT/ITEM-1",
        relationship_id=relationship_id,
    )


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
    relationship_ids = [m.relationship_id for m in members if m.item_id == "child"]
    assert relationship_ids == ["rel-1"]


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


def test_compare_baselines_keeps_same_item_different_uom_separate():
    result = _compare_baseline_pair(
        baseline_a=Baseline(
            id="bl-a",
            name="Baseline A",
            snapshot=_snapshot_with_child_uom("EA"),
        ),
        baseline_b=Baseline(
            id="bl-b",
            name="Baseline B",
            snapshot=_snapshot_with_child_uom("MM"),
        ),
        members_a=[_child_member(baseline_id="bl-a")],
        members_b=[_child_member(baseline_id="bl-b")],
    )

    assert result["summary"]["added"] == 1
    assert result["summary"]["removed"] == 1
    assert result["summary"]["changed"] == 0
    assert result["details"]["removed"][0]["uom"] == "EA"
    assert result["details"]["removed"][0]["bucket_key"] == "item-1::EA"
    assert result["details"]["added"][0]["uom"] == "MM"
    assert result["details"]["added"][0]["bucket_key"] == "item-1::MM"


def test_compare_baselines_uses_relationship_id_when_same_path_has_multiple_uoms():
    result = _compare_baseline_pair(
        baseline_a=Baseline(
            id="bl-a",
            name="Baseline A",
            snapshot=_snapshot_with_child_uom_lines(
                [("rel-a-ea", "EA"), ("rel-a-mm", "MM")]
            ),
        ),
        baseline_b=Baseline(
            id="bl-b",
            name="Baseline B",
            snapshot=_snapshot_with_child_uom_lines(
                [("rel-b-ea", "EA"), ("rel-b-kg", "KG")]
            ),
        ),
        members_a=[
            _child_member(
                baseline_id="bl-a",
                relationship_id="rel-a-ea",
                member_id="m-a-ea",
            ),
            _child_member(
                baseline_id="bl-a",
                relationship_id="rel-a-mm",
                member_id="m-a-mm",
            ),
        ],
        members_b=[
            _child_member(
                baseline_id="bl-b",
                relationship_id="rel-b-ea",
                member_id="m-b-ea",
            ),
            _child_member(
                baseline_id="bl-b",
                relationship_id="rel-b-kg",
                member_id="m-b-kg",
            ),
        ],
    )

    assert result["summary"]["added"] == 1
    assert result["summary"]["removed"] == 1
    assert result["summary"]["unchanged"] == 1
    assert result["details"]["removed"][0]["uom"] == "MM"
    assert result["details"]["added"][0]["uom"] == "KG"


def test_compare_baselines_normalizes_same_uom_bucket():
    result = _compare_baseline_pair(
        baseline_a=Baseline(
            id="bl-a",
            name="Baseline A",
            snapshot=_snapshot_with_child_uom(" ea "),
        ),
        baseline_b=Baseline(
            id="bl-b",
            name="Baseline B",
            snapshot=_snapshot_with_child_uom("EA"),
        ),
        members_a=[_child_member(baseline_id="bl-a")],
        members_b=[_child_member(baseline_id="bl-b")],
    )

    assert result["summary"] == {
        "added": 0,
        "removed": 0,
        "changed": 0,
        "unchanged": 1,
    }


def test_compare_baselines_defaults_missing_snapshot_uom_to_ea():
    result = _compare_baseline_pair(
        baseline_a=Baseline(
            id="bl-a",
            name="Baseline A",
            snapshot=_snapshot_with_child_uom(),
        ),
        baseline_b=Baseline(
            id="bl-b",
            name="Baseline B",
            snapshot=_snapshot_with_child_uom("EA"),
        ),
        members_a=[_child_member(baseline_id="bl-a")],
        members_b=[_child_member(baseline_id="bl-b")],
    )

    assert result["summary"]["added"] == 0
    assert result["summary"]["removed"] == 0
    assert result["summary"]["unchanged"] == 1


def test_compare_baselines_changed_row_exposes_uom_bucket():
    result = _compare_baseline_pair(
        baseline_a=Baseline(
            id="bl-a",
            name="Baseline A",
            snapshot=_snapshot_with_child_uom("mm"),
        ),
        baseline_b=Baseline(
            id="bl-b",
            name="Baseline B",
            snapshot=_snapshot_with_child_uom(" MM "),
        ),
        members_a=[_child_member(baseline_id="bl-a", generation=1)],
        members_b=[_child_member(baseline_id="bl-b", generation=2)],
    )

    assert result["summary"]["changed"] == 1
    changed = result["details"]["changed"][0]
    assert changed["uom"] == "MM"
    assert changed["bucket_key"] == "item-1::MM"
    assert changed["reference_id"] == "item-1"


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
        "added": [{"id": 1, "uom": "EA", "bucket_key": "item-1::EA"}],
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
    assert "uom" in text
    assert "bucket_key" in text
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
