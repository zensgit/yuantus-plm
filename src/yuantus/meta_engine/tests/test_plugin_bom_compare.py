from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.services.bom_service import BOMService


def _load_plugin_module():
    root = Path(__file__).resolve().parents[4]
    plugin_path = root / "plugins" / "yuantus-bom-compare" / "main.py"
    spec = importlib.util.spec_from_file_location("bom_compare_plugin", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _child(
    rel_id: str,
    child_id: str,
    qty: float,
    *,
    find_num: str | None = None,
    refdes: str | None = None,
) -> dict:
    props = {"quantity": qty}
    if find_num is not None:
        props["find_num"] = find_num
    if refdes is not None:
        props["refdes"] = refdes
    return {
        "relationship": {"id": rel_id, "properties": props},
        "child": {"id": child_id, "name": child_id, "children": []},
    }


def test_compare_summarized_aggregates_quantities():
    module = _load_plugin_module()
    tree_a = {"id": "root", "children": [_child("rel1", "c1", 1), _child("rel2", "c1", 2)]}
    tree_b = {"id": "root", "children": [_child("rel3", "c1", 1)]}

    result = module.compare_bom_trees(
        tree_a,
        tree_b,
        mode="summarized",
        quantity_key="quantity",
        position_key="find_num",
        refdes_key="refdes",
        include_unchanged=True,
    )

    assert result.summary["modified"] == 1
    assert result.differences[0].qty_a == 3.0
    assert result.differences[0].qty_b == 1.0


def test_compare_num_qty_treats_quantity_as_key():
    module = _load_plugin_module()
    tree_a = {"id": "root", "children": [_child("rel1", "c1", 1)]}
    tree_b = {"id": "root", "children": [_child("rel2", "c1", 2)]}

    result = module.compare_bom_trees(
        tree_a,
        tree_b,
        mode="num_qty",
        quantity_key="quantity",
        position_key="find_num",
        refdes_key="refdes",
        include_unchanged=True,
    )

    assert result.summary["added"] == 1
    assert result.summary["removed"] == 1
    assert result.summary["modified"] == 0


def test_compare_by_item_rolls_up_child_id_across_positions():
    module = _load_plugin_module()
    line_key, props, aggregate = BOMService.resolve_compare_mode("by_item")
    assert line_key == "child_id"
    assert props == ["quantity", "uom"]
    assert aggregate is True
    assert BOMService.resolve_compare_mode("child_id") == (line_key, props, aggregate)

    tree_a = {
        "id": "root",
        "children": [
            _child("rel1", "c1", 1, find_num="10"),
            _child("rel2", "c1", 1, find_num="20"),
        ],
    }
    tree_b = {"id": "root", "children": [_child("rel3", "c1", 2, find_num="99")]}

    result = module.compare_bom_trees(
        tree_a,
        tree_b,
        mode="by_item",
        quantity_key="quantity",
        position_key="find_num",
        refdes_key="refdes",
        include_unchanged=True,
    )

    assert result.summary == {"added": 0, "removed": 0, "modified": 0, "unchanged": 1}
    assert result.differences[0].status == "unchanged"
    assert result.differences[0].qty_a == 2.0
    assert result.differences[0].qty_b == 2.0


def test_compare_by_find_refdes_mode_and_alias_behaves_as_expected():
    line_key, props, aggregate = BOMService.resolve_compare_mode("by_find_refdes")
    assert line_key == "child_config_find_refdes"
    assert props == ["quantity", "uom", "find_num", "refdes"]
    assert aggregate is False
    assert BOMService.resolve_compare_mode("child_config_find_refdes") == (
        line_key,
        props,
        aggregate,
    )

    service = BOMService(MagicMock())
    tree_a = {
        "id": "root",
        "config_id": "root",
        "children": [_child("rel1", "c1", 1, find_num="10", refdes="r2,r1")],
    }
    tree_b = {
        "id": "root",
        "config_id": "root",
        "children": [_child("rel2", "c1", 2, find_num="10", refdes="R1,R2")],
    }

    result = service.compare_bom_trees(
        tree_a,
        tree_b,
        include_relationship_props=props,
        line_key=line_key,
        aggregate_quantities=aggregate,
    )

    assert result["summary"] == {
        "added": 0,
        "removed": 0,
        "changed": 1,
        "changed_major": 1,
        "changed_minor": 0,
        "changed_info": 0,
    }
    assert len(result["changed"]) == 1
    assert result["changed"][0]["line_key"] == "root::c1::10::R1,R2"
    assert result["changed"][0]["before"] == {"quantity": 1}
    assert result["changed"][0]["after"] == {"quantity": 2}


def test_compare_mode_error_lists_by_find_refdes():
    with pytest.raises(ValueError, match="by_find_refdes"):
        BOMService.resolve_compare_mode("not_a_mode")


def test_compare_only_product_skips_unchanged():
    module = _load_plugin_module()
    tree_a = {"id": "root", "children": [_child("rel1", "c1", 1)]}
    tree_b = {"id": "root", "children": [_child("rel2", "c1", 5)]}

    result = module.compare_bom_trees(
        tree_a,
        tree_b,
        mode="only_product",
        quantity_key="quantity",
        position_key="find_num",
        refdes_key="refdes",
        include_unchanged=False,
    )

    assert result.summary["unchanged"] == 1
    assert result.differences == []


def test_compare_quantity_tolerance_allows_small_delta():
    module = _load_plugin_module()
    tree_a = {"id": "root", "children": [_child("rel1", "c1", 1.0)]}
    tree_b = {"id": "root", "children": [_child("rel2", "c1", 1.4)]}

    result = module.compare_bom_trees(
        tree_a,
        tree_b,
        mode="summarized",
        quantity_key="quantity",
        position_key="find_num",
        refdes_key="refdes",
        include_unchanged=True,
        quantity_tolerance=0.5,
    )

    assert result.summary["unchanged"] == 1
    assert result.differences[0].status == "unchanged"


def test_compare_filters_exclude_added():
    module = _load_plugin_module()
    tree_a = {"id": "root", "children": []}
    tree_b = {"id": "root", "children": [_child("rel2", "c1", 1)]}
    filters = module.BomCompareFilters(exclude_statuses=["added"])

    result = module.compare_bom_trees(
        tree_a,
        tree_b,
        mode="summarized",
        quantity_key="quantity",
        position_key="find_num",
        refdes_key="refdes",
        include_unchanged=True,
        filters=filters,
    )

    assert result.summary["added"] == 1
    assert result.differences == []
    assert result.summary_filtered == {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}


def test_export_csv_payload_joins_lists():
    module = _load_plugin_module()
    diffs = [
        module.BomCompareDiff(
            key="c1",
            child_id="c1",
            name="Child 1",
            status="added",
            relationship_ids_a=["rel-a", "rel-b"],
            relationship_ids_b=[],
        )
    ]
    csv_text = module._build_csv_payload(
        diffs,
        columns=["key", "relationship_ids_a", "relationship_ids_b"],
        delimiter=",",
    )
    lines = csv_text.strip().splitlines()
    assert lines[0] == "key,relationship_ids_a,relationship_ids_b"
    assert lines[1] == "c1,rel-a|rel-b,"


def test_normalize_export_columns_rejects_unknown():
    module = _load_plugin_module()
    with pytest.raises(ValueError):
        module._normalize_export_columns(["bad_column"])


def test_normalize_export_columns_excludes_fields():
    module = _load_plugin_module()
    columns = module._normalize_export_columns(
        ["key", "status", "child_id"], exclude_columns=["status"]
    )
    assert columns == ["key", "child_id"]


def test_normalize_export_format_accepts_xlsx():
    module = _load_plugin_module()
    assert module._normalize_export_format("xlsx") == "xlsx"


def test_build_xlsx_payload_when_available():
    module = _load_plugin_module()
    if importlib.util.find_spec("openpyxl") is None:
        pytest.skip("openpyxl not installed")
    diffs = [
        module.BomCompareDiff(
            key="c1",
            child_id="c1",
            name="Child 1",
            status="added",
        )
    ]
    payload = module._build_xlsx_payload(
        diffs,
        columns=["key", "status", "child_id", "name"],
        summary={"added": 1, "removed": 0, "modified": 0, "unchanged": 0},
    )
    assert payload[:2] == b"PK"
