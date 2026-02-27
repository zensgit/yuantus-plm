from __future__ import annotations

from unittest.mock import MagicMock

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
    ops = delta["operations"]
    assert {op["op"] for op in ops} == {"add", "remove", "update"}
    update_op = [op for op in ops if op["op"] == "update"][0]
    assert update_op["changes"][0]["field"] == "quantity"
    assert update_op["changes"][0]["before"] == 2
    assert update_op["changes"][0]["after"] == 4


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
