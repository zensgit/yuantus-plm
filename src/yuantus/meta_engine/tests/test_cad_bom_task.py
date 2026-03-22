import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.tasks import cad_pipeline_tasks


def test_cad_bom_task_marks_review_pending_for_partial_import_and_persists_summary():
    session = MagicMock()
    file_container = SimpleNamespace(
        id="file-1",
        system_path="/vault/file-1.step",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_bom_path=None,
        cad_review_state="approved",
        cad_review_note="looks good",
        cad_review_by_id=99,
        cad_reviewed_at=object(),
    )
    session.get.return_value = file_container

    partial_import = {
        "ok": True,
        "created_items": 1,
        "existing_items": 0,
        "created_lines": 1,
        "skipped_lines": 2,
        "errors": [],
        "contract_validation": {
            "schema": "nodes_edges_v1",
            "status": "invalid",
            "shape": "graph",
            "raw_counts": {"nodes": 3, "edges": 2},
            "accepted_counts": {"nodes": 2, "edges": 1},
            "root": "assy-root",
            "root_source": "inferred",
            "issues": ["edge[1] child not found: child-missing"],
        },
    }

    with patch.object(cad_pipeline_tasks, "_ensure_source_exists"):
        with patch.object(cad_pipeline_tasks, "_cad_connector_enabled", return_value=True):
            with patch.object(
                cad_pipeline_tasks,
                "_call_cad_connector_convert",
                return_value={"bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"}},
            ):
                with patch.object(cad_pipeline_tasks, "FileService") as file_service_cls:
                    with patch.object(cad_pipeline_tasks, "CadBomImportService") as importer_cls:
                        file_service_cls.return_value.upload_file.return_value = "/stored/cad_bom/file-1.json"
                        importer_cls.return_value.import_bom.return_value = partial_import

                        result = cad_pipeline_tasks.cad_bom(
                            {"file_id": "file-1", "item_id": "item-1", "user_id": 7},
                            session,
                        )

    assert result["summary"]["status"] == "degraded"
    assert result["summary"]["needs_operator_review"] is True
    assert file_container.cad_bom_path == "/stored/cad_bom/file-1.json"
    assert file_container.cad_review_state == "pending"
    assert file_container.cad_review_note == "CAD BOM import requires operator review"
    assert file_container.cad_review_by_id is None
    assert file_container.cad_reviewed_at is None

    stored_file_obj = file_service_cls.return_value.upload_file.call_args.kwargs["file_obj"]
    stored_payload = json.loads(stored_file_obj.getvalue().decode("utf-8"))
    assert stored_payload["summary"]["status"] == "degraded"
    assert stored_payload["summary"]["issue_codes"] == [
        "contract_invalid",
        "edge_reference_missing",
        "skipped_lines",
    ]
