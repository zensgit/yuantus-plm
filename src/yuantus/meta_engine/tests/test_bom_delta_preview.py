from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.services.bom_service import BOMService


def test_build_delta_preview_converts_compare_payload_to_patch_operations():
    service = BOMService(MagicMock())
    compare_result = {
        "summary": {"added": 1, "removed": 1, "changed": 1},
        "added": [
            {
                "line_key": "k-add",
                "parent_id": "p1",
                "child_id": "c1",
                "relationship_id": "r1",
                "properties": {"quantity": 2},
            }
        ],
        "removed": [
            {
                "line_key": "k-del",
                "parent_id": "p2",
                "child_id": "c2",
                "relationship_id": "r2",
                "properties": {"quantity": 1},
            }
        ],
        "changed": [
            {
                "line_key": "k-upd",
                "parent_id": "p3",
                "child_id": "c3",
                "relationship_id": "r3",
                "severity": "major",
                "changes": [
                    {
                        "field": "quantity",
                        "left": 2,
                        "right": 4,
                        "severity": "major",
                    }
                ],
            }
        ],
    }

    delta = service.build_delta_preview(compare_result)

    assert delta["summary"]["total_ops"] == 3
    assert delta["summary"]["adds"] == 1
    assert delta["summary"]["removes"] == 1
    assert delta["summary"]["updates"] == 1
    assert delta["summary"]["risk_level"] in {"high", "critical", "medium", "low", "none"}
    assert delta["summary"]["risk_distribution"]["medium"] == 2
    assert delta["summary"]["risk_distribution"]["high"] == 1
    assert delta["change_summary"]["ops"]["updates"] == 1
    assert delta["change_summary"]["severity"]["major"] == 1
    assert delta["change_summary"]["risk_distribution"]["medium"] == 2
    assert delta["change_summary"]["risk_distribution"]["high"] == 1
    ops = delta["operations"]
    assert {op["op"] for op in ops} == {"add", "remove", "update"}
    add_op = [op for op in ops if op["op"] == "add"][0]
    remove_op = [op for op in ops if op["op"] == "remove"][0]
    assert add_op["risk_level"] == "medium"
    assert remove_op["risk_level"] == "medium"
    update_op = [op for op in ops if op["op"] == "update"][0]
    assert update_op["changes"][0]["field"] == "quantity"
    assert update_op["changes"][0]["before"] == 2
    assert update_op["changes"][0]["after"] == 4
    assert update_op["change_count"] == 1
    assert update_op["risk_level"] in {"high", "medium", "low"}


def test_export_delta_csv_renders_rows_for_all_ops():
    service = BOMService(MagicMock())
    delta = {
        "summary": {"total_ops": 2, "adds": 1, "removes": 0, "updates": 1},
        "operations": [
            {
                "op": "add",
                "line_key": "k-add",
                "parent_id": "p1",
                "child_id": "c1",
                "relationship_id": "r1",
            },
            {
                "op": "update",
                "line_key": "k-upd",
                "parent_id": "p2",
                "child_id": "c2",
                "relationship_id": "r2",
                "severity": "major",
                "changes": [
                    {
                        "field": "quantity",
                        "before": 1,
                        "after": 3,
                    }
                ],
            },
        ],
    }

    csv_text = service.export_delta_csv(delta)
    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]

    assert lines[0].startswith("op,line_key,parent_id,child_id,relationship_id")
    assert any(line.startswith("add,k-add,p1,c1,r1") for line in lines[1:])
    assert any("update,k-upd,p2,c2,r2" in line and "quantity" in line for line in lines[1:])


def test_export_delta_csv_supports_field_filter():
    service = BOMService(MagicMock())
    delta = {
        "summary": {"total_ops": 1, "adds": 0, "removes": 0, "updates": 1},
        "operations": [
            {
                "op": "update",
                "line_key": "k-upd",
                "parent_id": "p2",
                "child_id": "c2",
                "relationship_id": "r2",
                "severity": "major",
                "risk_level": "high",
                "change_count": 1,
                "changes": [
                    {
                        "field": "quantity",
                        "before": 1,
                        "after": 3,
                    }
                ],
            },
        ],
    }
    csv_text = service.export_delta_csv(
        delta,
        fields=["op", "line_key", "risk_level", "field", "before", "after"],
    )
    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    assert lines[0] == "op,line_key,risk_level,field,before,after"
    assert any("update,k-upd,high,quantity,1,3" in line for line in lines[1:])


def test_filter_delta_preview_fields_validates_field_name():
    service = BOMService(MagicMock())
    with pytest.raises(ValueError, match="unsupported key"):
        service.filter_delta_preview_fields({"operations": []}, ["op", "unknown"])


def test_export_delta_markdown_renders_summary_and_operations():
    service = BOMService(MagicMock())
    delta = {
        "summary": {
            "total_ops": 2,
            "adds": 1,
            "removes": 0,
            "updates": 1,
            "risk_level": "high",
            "risk_distribution": {"high": 1, "medium": 1, "low": 0, "none": 0, "critical": 0},
        },
        "change_summary": {"ops": {"adds": 1, "updates": 1}},
        "compare_summary": {"added": 1, "changed": 1},
        "operations": [
            {
                "op": "add",
                "line_key": "k-add",
                "parent_id": "p1",
                "child_id": "c1",
                "relationship_id": "r1",
                "risk_level": "medium",
            },
            {
                "op": "update",
                "line_key": "k-upd",
                "parent_id": "p2",
                "child_id": "c2",
                "relationship_id": "r2",
                "severity": "major",
                "risk_level": "high",
                "changes": [{"field": "quantity", "before": 1, "after": 3}],
            },
        ],
    }

    md_text = service.export_delta_markdown(
        delta,
        fields=["op", "line_key", "risk_level", "field", "before", "after"],
    )

    assert md_text.startswith("# BOM Delta Preview")
    assert "## Summary" in md_text
    assert "risk_distribution" in md_text
    assert "| op | line_key | risk_level | field | before | after |" in md_text
    assert "| add | k-add | medium |  |  |  |" in md_text
    assert "| update | k-upd | high | quantity | 1 | 3 |" in md_text


def test_export_delta_markdown_handles_empty_operations():
    service = BOMService(MagicMock())
    delta = {
        "summary": {"total_ops": 0, "risk_level": "none"},
        "change_summary": {},
        "operations": [],
    }
    md_text = service.export_delta_markdown(delta)
    assert "_No operations_" in md_text
