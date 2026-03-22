from types import SimpleNamespace
from unittest.mock import MagicMock

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.cad_bom_import_service import (
    CadBomImportService,
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
