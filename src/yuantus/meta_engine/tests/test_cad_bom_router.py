import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import ItemFile
from yuantus.meta_engine.web.cad_router import router as cad_router


def _cad_client(*, file_container, jobs=None, item_file_rows=None) -> TestClient:
    mock_db = MagicMock()
    mock_db.get.return_value = file_container

    job_query = MagicMock()
    job_query.filter.return_value = job_query
    job_query.order_by.return_value = job_query
    job_query.limit.return_value = job_query
    job_query.all.return_value = jobs or []

    item_file_query = MagicMock()
    item_file_query.filter.return_value = item_file_query
    item_file_query.order_by.return_value = item_file_query
    item_file_query.all.return_value = item_file_rows or []

    def _query(model):
        if model is ItemFile:
            return item_file_query
        return job_query

    mock_db.query.side_effect = _query

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def override_get_current_user():
        return CurrentUser(
            id=7,
            tenant_id="tenant-a",
            org_id="org-a",
            username="tester",
            email=None,
            roles=["engineer"],
        )

    app = FastAPI()
    app.include_router(cad_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def test_get_cad_bom_returns_stored_contract_validation_summary():
    client = _cad_client(file_container=SimpleNamespace(id="file-1", cad_bom_path="/vault/file-1.json"))
    stored_payload = {
        "file_id": "file-1",
        "item_id": "item-1",
        "imported_at": "2026-03-22T00:00:00Z",
        "import_result": {
            "ok": True,
            "contract_validation": {
                "schema": "nodes_edges_v1",
                "status": "invalid",
                "shape": "graph",
                "raw_counts": {"nodes": 3, "edges": 2},
                "accepted_counts": {"nodes": 2, "edges": 1},
                "root": "assy-root",
                "root_source": "inferred",
                "issues": ["edge[0] child not found: child-missing"],
            },
        },
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        def _download(_path, output_stream):
            output_stream.write(json.dumps(stored_payload).encode("utf-8"))

        file_service_cls.return_value.download_file.side_effect = _download
        response = client.get("/api/v1/cad/files/file-1/bom")

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == "file-1"
    assert body["job_status"] == "completed"
    assert body["import_result"]["contract_validation"] == stored_payload["import_result"][
        "contract_validation"
    ]
    assert body["summary"]["status"] == "degraded"
    assert body["summary"]["needs_operator_review"] is True
    assert body["summary"]["issue_codes"] == ["contract_invalid", "edge_reference_missing"]
    action_codes = [action["code"] for action in body["summary"]["recovery_actions"]]
    assert "repair_edge_references" in action_codes
    assert "inspect_raw_cad_bom" in action_codes


def test_get_cad_bom_job_fallback_preserves_contract_validation():
    client = _cad_client(
        file_container=SimpleNamespace(id="file-2", cad_bom_path=None),
        jobs=[
            SimpleNamespace(
                id="job-1",
                status="completed",
                created_at=None,
                completed_at=None,
                payload={
                    "file_id": "file-2",
                    "item_id": "item-2",
                    "result": {
                        "import_result": {
                            "ok": True,
                            "contract_validation": {
                                "schema": "nodes_edges_v1",
                                "status": "valid",
                                "shape": "tree",
                                "raw_counts": {"nodes": 2, "edges": 1},
                                "accepted_counts": {"nodes": 2, "edges": 1},
                                "root": "assy-root",
                                "root_source": "payload",
                                "issues": [],
                            },
                        },
                        "bom": {"root": {"id": "assy-root", "children": [{"id": "child-1"}]}},
                    },
                },
            )
        ],
    )

    response = client.get("/api/v1/cad/files/file-2/bom")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "job-1"
    assert body["job_status"] == "completed"
    assert body["import_result"]["contract_validation"]["status"] == "valid"
    assert body["import_result"]["contract_validation"]["shape"] == "tree"
    assert body["summary"]["status"] == "ready"
    assert body["summary"]["needs_operator_review"] is False


def test_reimport_cad_bom_uses_stored_item_id_and_logs_request():
    file_container = SimpleNamespace(
        id="file-3",
        cad_bom_path="/vault/file-3.json",
        system_path="/vault/file-3.step",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
    )
    client = _cad_client(file_container=file_container)
    stored_payload = {
        "file_id": "file-3",
        "item_id": "item-from-stored-bom",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch("yuantus.meta_engine.web.cad_router.JobService") as job_service_cls:
            def _download(_path, output_stream):
                output_stream.write(json.dumps(stored_payload).encode("utf-8"))

            file_service_cls.return_value.download_file.side_effect = _download
            job_service_cls.return_value.create_job.return_value = SimpleNamespace(
                id="job-reimport",
                status="queued",
            )
            response = client.post("/api/v1/cad/files/file-3/bom/reimport", json={})

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "file_id": "file-3",
        "item_id": "item-from-stored-bom",
        "job_id": "job-reimport",
        "job_status": "queued",
    }
    payload = job_service_cls.return_value.create_job.call_args.kwargs["payload"]
    assert payload["item_id"] == "item-from-stored-bom"
    assert payload["file_id"] == "file-3"


def test_reimport_cad_bom_returns_400_when_attached_item_resolution_is_ambiguous():
    file_container = SimpleNamespace(
        id="file-4",
        cad_bom_path=None,
        system_path="/vault/file-4.step",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
    )
    client = _cad_client(
        file_container=file_container,
        item_file_rows=[
            SimpleNamespace(item_id="item-a"),
            SimpleNamespace(item_id="item-b"),
        ],
    )

    response = client.post("/api/v1/cad/files/file-4/bom/reimport", json={})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "cad_bom_reimport_item_ambiguous"
    assert detail["context"]["item_ids"] == ["item-a", "item-b"]
