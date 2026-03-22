import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.web.cad_router import router as cad_router


def _cad_client(*, file_container, jobs=None) -> TestClient:
    mock_db = MagicMock()
    mock_db.get.return_value = file_container
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = jobs or []
    mock_db.query.return_value = query

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
