from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.cad_bom_import_service import (
    CadBomImportService,
    build_cad_bom_mismatch_analysis,
    build_cad_bom_operator_summary,
    prepare_cad_bom_payload,
)


def _service() -> CadBomImportService:
    root_item = SimpleNamespace(id="item-root", permission_id="perm-root")
    part_type = SimpleNamespace(properties=[])
    session = MagicMock()

    def _get(model, key):
        if model is Item and key == "item-root":
            return root_item
        if model is ItemType and key == "Part":
            return part_type
        return None

    session.get.side_effect = _get
    service = CadBomImportService(session)
    service.bom_service = MagicMock()
    return service


def test_prepare_cad_bom_payload_reports_ambiguous_root_binding_for_graph():
    nodes, edges, root, validation = prepare_cad_bom_payload(
        {
            "nodes": [{"id": "top-a"}, {"id": "top-b"}],
            "edges": [],
        }
    )

    assert [node["id"] for node in nodes] == ["top-a", "top-b"]
    assert edges == []
    assert root is None
    assert validation["status"] == "invalid"
    assert validation["shape"] == "graph"
    assert validation["accepted_counts"] == {"nodes": 2, "edges": 0}
    assert "ambiguous root binding: top-a, top-b" in validation["issues"]


def test_import_bom_infers_root_for_graph_payload_and_keeps_import_flow():
    service = _service()

    result = service.import_bom(
        root_item_id="item-root",
        bom_payload={
            "nodes": [{"id": "assy-root"}, {"id": "child-1"}],
            "edges": [{"parent": "assy-root", "child": "child-1", "qty": 2}],
        },
        user_id=7,
    )

    assert result["created_items"] == 1
    assert result["created_lines"] == 1
    assert result["skipped_lines"] == 0
    assert result["contract_validation"] == {
        "schema": "nodes_edges_v1",
        "status": "valid",
        "shape": "graph",
        "raw_counts": {"nodes": 2, "edges": 1},
        "accepted_counts": {"nodes": 2, "edges": 1},
        "root": "assy-root",
        "root_source": "inferred",
        "issues": [],
    }
    service.bom_service.add_child.assert_called_once()
    args, kwargs = service.bom_service.add_child.call_args
    assert args[:2] == ("item-root", service.session.add.call_args[0][0].id)
    assert kwargs["quantity"] == 2.0


def test_import_bom_records_contract_validation_for_invalid_entries_without_crashing():
    service = _service()

    result = service.import_bom(
        root_item_id="item-root",
        bom_payload={
            "nodes": [{"id": "assy-root"}, "bad-node", {"id": "child-1"}, {"id": "child-1"}],
            "edges": [
                "bad-edge",
                {"parent": "assy-root", "child": "missing-child"},
                {"parent": "assy-root", "child": "child-1"},
            ],
        },
        user_id=7,
    )

    assert result["created_items"] == 1
    assert result["created_lines"] == 1
    assert result["skipped_lines"] == 1
    validation = result["contract_validation"]
    assert validation["status"] == "invalid"
    assert validation["raw_counts"] == {"nodes": 4, "edges": 3}
    assert validation["accepted_counts"] == {"nodes": 2, "edges": 1}
    assert validation["root"] == "assy-root"
    assert validation["root_source"] == "inferred"
    assert "node[1] must be an object" in validation["issues"]
    assert "duplicate node id: child-1" in validation["issues"]
    assert "edge[0] must be an object" in validation["issues"]
    assert "edge[1] child not found: missing-child" in validation["issues"]


def test_build_cad_bom_operator_summary_returns_recovery_actions_for_invalid_contract():
    summary = build_cad_bom_operator_summary(
        import_result={
            "created_lines": 1,
            "skipped_lines": 2,
            "errors": ["BOM relationship already exists"],
            "contract_validation": {
                "schema": "nodes_edges_v1",
                "status": "invalid",
                "shape": "graph",
                "raw_counts": {"nodes": 4, "edges": 3},
                "accepted_counts": {"nodes": 2, "edges": 1},
                "root": None,
                "root_source": None,
                "issues": [
                    "duplicate node id: assy-root",
                    "ambiguous root binding: top-a, top-b",
                    "edge[1] child not found: child-missing",
                ],
            },
        },
        bom_payload={"nodes": [{"id": "top-a"}], "edges": []},
        has_artifact=True,
    )

    assert summary["status"] == "degraded"
    assert summary["recoverable"] is True
    assert summary["issue_count"] == 3
    assert summary["error_count"] == 1
    assert summary["skipped_lines"] == 2
    assert summary["accepted_counts"] == {"nodes": 2, "edges": 1}
    codes = [action["code"] for action in summary["recovery_actions"]]
    assert "dedupe_node_ids" in codes
    assert "repair_root_binding" in codes
    assert "repair_edge_references" in codes
    assert "review_import_errors" in codes
    assert "inspect_raw_cad_bom" in codes
    assert "rerun_cad_bom_import" in codes


def test_build_cad_bom_mismatch_analysis_reports_quantity_drift_against_live_bom():
    root_item = SimpleNamespace(
        id="item-root",
        config_id="cfg-root",
        properties={"item_number": "ASSY-1", "name": "Assembly"},
    )
    child_item = SimpleNamespace(
        id="item-child",
        config_id="cfg-child",
        properties={"item_number": "CH-1", "name": "Child"},
    )
    session = MagicMock()

    def _get(model, key):
        if model is Item and key == "item-root":
            return root_item
        return None

    session.get.side_effect = _get
    item_query = MagicMock()
    item_query.filter.return_value = item_query
    item_query.first.return_value = child_item
    session.query.return_value = item_query

    live_tree = {
        "id": "item-root",
        "config_id": "cfg-root",
        "item_number": "ASSY-1",
        "name": "Assembly",
        "children": [
            {
                "relationship": {
                    "id": "rel-live-1",
                    "properties": {"quantity": 1.0, "uom": "EA"},
                },
                "child": {
                    "id": "item-child",
                    "config_id": "cfg-child",
                    "item_number": "CH-1",
                    "name": "Child",
                    "children": [],
                },
            }
        ],
    }

    with patch(
        "yuantus.meta_engine.services.cad_bom_import_service.BOMService.get_bom_structure",
        return_value=live_tree,
    ):
        analysis = build_cad_bom_mismatch_analysis(
            session=session,
            root_item_id="item-root",
            bom_payload={
                "nodes": [
                    {"id": "assy-root", "part_number": "ASSY-1"},
                    {"id": "child-1", "part_number": "CH-1"},
                ],
                "edges": [{"parent": "assy-root", "child": "child-1", "qty": 2, "uom": "EA"}],
            },
        )

    assert analysis["status"] == "mismatch"
    assert analysis["analysis_scope"] == "full_payload"
    assert analysis["line_key"] == "child_id_find_refdes"
    assert analysis["recoverable"] is True
    assert analysis["summary"]["updates"] == 1
    assert analysis["compare_summary"]["changed"] == 1
    assert analysis["grouped_counters"]["quantity"] == 1
    assert analysis["mismatch_groups"] == ["line_value_mismatch"]
    assert analysis["issue_codes"] == ["live_bom_quantity_mismatch"]
    action_codes = [action["code"] for action in analysis["recovery_actions"]]
    assert "review_live_bom_quantities" in action_codes
    assert "open_cad_operator_proof_surface" in action_codes
    assert "open_cad_bom_mismatch_surface" in action_codes
    assert "export_mismatch_proof_bundle" in action_codes


def test_build_cad_bom_mismatch_analysis_returns_unresolved_contract_without_item_binding():
    analysis = build_cad_bom_mismatch_analysis(
        session=MagicMock(),
        root_item_id=None,
        bom_payload={"nodes": [{"id": "root"}], "edges": []},
    )

    assert analysis["status"] == "unresolved"
    assert analysis["reason"] == "item_binding_missing"
    assert analysis["line_key"] == "child_id_find_refdes"
    assert analysis["summary"]["total_ops"] == 0
    assert analysis["delta_preview"]["summary"]["risk_level"] == "none"
    assert analysis["live_bom"] == {}
