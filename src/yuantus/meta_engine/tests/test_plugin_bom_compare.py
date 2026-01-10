from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_plugin_module():
    root = Path(__file__).resolve().parents[4]
    plugin_path = root / "plugins" / "yuantus-bom-compare" / "main.py"
    spec = importlib.util.spec_from_file_location("bom_compare_plugin", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _child(rel_id: str, child_id: str, qty: float) -> dict:
    return {
        "relationship": {"id": rel_id, "properties": {"quantity": qty}},
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
