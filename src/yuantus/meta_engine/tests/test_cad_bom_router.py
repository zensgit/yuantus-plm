import json
import io
import zipfile
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import ItemFile
from yuantus.meta_engine.web.cad_router import router as cad_router


def _sample_mismatch(
    *,
    status="match",
    total_ops=0,
    adds=0,
    removes=0,
    updates=0,
    issue_codes=None,
    recovery_actions=None,
    rows=None,
    risk_level="none",
):
    return {
        "status": status,
        "reason": None,
        "analysis_scope": "full_payload",
        "root_item_id": "item-1",
        "line_key": "child_id_find_refdes",
        "recoverable": total_ops > 0,
        "contract_status": "valid",
        "summary": {
            "total_ops": total_ops,
            "adds": adds,
            "removes": removes,
            "updates": updates,
            "risk_level": risk_level,
        },
        "compare_summary": {"added": adds, "removed": removes, "changed": updates},
        "grouped_counters": {
            "structure": adds + removes,
            "quantity": updates,
            "uom": 0,
            "other": 0,
        },
        "rows": rows or [],
        "delta_preview": {"summary": {"total_ops": total_ops, "risk_level": risk_level}},
        "issue_codes": issue_codes or [],
        "mismatch_groups": (
            ["missing_in_live_bom"] * bool(adds)
            + ["extra_in_live_bom"] * bool(removes)
            + ["line_value_mismatch"] * bool(updates)
        ),
        "recovery_actions": recovery_actions or [],
        "live_bom": {"id": "item-1", "children": []},
    }


def _cad_client(*, file_container, jobs=None, item_file_rows=None, history_logs=None) -> TestClient:
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

    history_query = MagicMock()
    history_query.filter.return_value = history_query
    history_query.order_by.return_value = history_query
    history_query.limit.return_value = history_query
    history_query.all.return_value = history_logs or []

    def _query(model):
        if model is ItemFile:
            return item_file_query
        if model is CadChangeLog:
            return history_query
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
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=1,
                updates=1,
                issue_codes=["live_bom_quantity_mismatch"],
                recovery_actions=[{"code": "review_live_bom_quantities", "label": "Review drift."}],
                rows=[{"line_key": "assy-root::child-1", "status": "changed"}],
                risk_level="medium",
            ),
        ):
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
    assert body["mismatch"]["status"] == "mismatch"
    assert body["mismatch"]["issue_codes"] == ["live_bom_quantity_mismatch"]
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

    with patch(
        "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
        return_value=_sample_mismatch(status="match"),
    ):
        response = client.get("/api/v1/cad/files/file-2/bom")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "job-1"
    assert body["job_status"] == "completed"
    assert body["import_result"]["contract_validation"]["status"] == "valid"
    assert body["import_result"]["contract_validation"]["shape"] == "tree"
    assert body["summary"]["status"] == "ready"
    assert body["summary"]["needs_operator_review"] is False
    assert body["mismatch"]["status"] == "match"


def test_get_cad_bom_mismatch_returns_links_and_unresolved_status():
    client = _cad_client(file_container=SimpleNamespace(id="file-m1", cad_bom_path="/vault/file-m1.json"))
    stored_payload = {
        "file_id": "file-m1",
        "item_id": None,
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value={
                **_sample_mismatch(status="unresolved"),
                "reason": "item_binding_missing",
                "recoverable": False,
            },
        ):
            def _download(_path, output_stream):
                output_stream.write(json.dumps(stored_payload).encode("utf-8"))

            file_service_cls.return_value.download_file.side_effect = _download
            response = client.get("/api/v1/cad/files/file-m1/bom/mismatch")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unresolved"
    assert body["reason"] == "item_binding_missing"
    assert body["links"]["mismatch_url"] == "/api/v1/cad/files/file-m1/bom/mismatch"
    assert body["links"]["reimport_url"] == "/api/v1/cad/files/file-m1/bom/reimport"


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


def test_export_cad_bom_bundle_zip_includes_summary_review_and_history():
    file_container = SimpleNamespace(
        id="file-5",
        filename="assy.step",
        cad_bom_path="/vault/file-5.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs operator cleanup",
        cad_review_by_id=9,
        cad_reviewed_at=datetime(2026, 3, 22, 10, 0, 0),
    )
    client = _cad_client(
        file_container=file_container,
        history_logs=[
            SimpleNamespace(
                id="log-1",
                action="cad_bom_reimport_requested",
                payload={"job_id": "job-r1"},
                created_at=datetime(2026, 3, 22, 9, 30, 0),
                user_id=7,
            )
        ],
    )
    stored_payload = {
        "file_id": "file-5",
        "item_id": "item-5",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {
            "ok": True,
            "errors": ["line skipped"],
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
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=2,
                adds=1,
                updates=1,
                issue_codes=["live_bom_structure_mismatch", "live_bom_quantity_mismatch"],
                recovery_actions=[
                    {"code": "review_live_bom_structure", "label": "Review structure."},
                    {"code": "review_live_bom_quantities", "label": "Review quantities."},
                ],
                rows=[
                    {
                        "line_key": "assy-root::child-1",
                        "parent_id": "item-root",
                        "child_id": "item-child",
                        "status": "changed",
                        "quantity_before": 1.0,
                        "quantity_after": 2.0,
                        "quantity_delta": 1.0,
                        "uom_before": "EA",
                        "uom_after": "EA",
                        "severity": "major",
                        "change_fields": ["quantity"],
                    }
                ],
                risk_level="high",
            ),
        ):
            def _download(_path, output_stream):
                output_stream.write(json.dumps(stored_payload).encode("utf-8"))

            file_service_cls.return_value.download_file.side_effect = _download
            response = client.get("/api/v1/cad/files/file-5/bom/export?export_format=zip")

    assert response.status_code == 200
    assert response.headers.get("content-disposition", "").endswith("cad-bom-ops-file-5.zip\"")

    zf = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(zf.namelist())
    assert "bundle.json" in names
    assert "mismatch.json" in names
    assert "live_bom.json" in names
    assert "mismatch_delta.csv" in names
    assert "mismatch_rows.csv" in names
    assert "mismatch_delta_preview.json" in names
    assert "proof_manifest.json" in names
    assert "summary.json" in names
    assert "review.json" in names
    assert "history.csv" in names
    assert "recovery_actions.csv" in names
    assert "README.txt" in names

    bundle = json.loads(zf.read("bundle.json"))
    assert bundle["file"]["file_id"] == "file-5"
    assert bundle["review"]["state"] == "pending"
    assert bundle["cad_bom"]["summary"]["status"] == "degraded"
    assert bundle["cad_bom"]["mismatch"]["status"] == "mismatch"
    assert bundle["proof_manifest"]["bundle_kind"] == "cad_bom_mismatch_proof"
    assert bundle["proof_manifest"]["mismatch_grouped_counters"]["structure"] == 1
    assert bundle["proof_manifest"]["mismatch_line_key"] == "child_id_find_refdes"
    assert bundle["proof_manifest"]["proof_files"][-1] == "README.txt"
    assert bundle["history"][0]["action"] == "cad_bom_reimport_requested"

    history_csv = zf.read("history.csv").decode("utf-8-sig")
    assert history_csv.splitlines()[0] == "id,action,created_at,user_id,payload"
    assert "cad_bom_reimport_requested" in history_csv

    readme = zf.read("README.txt").decode("utf-8")
    assert "structured_bom_url=/api/v1/cad/files/file-5/bom" in readme
    assert "mismatch_url=/api/v1/cad/files/file-5/bom/mismatch" in readme
    assert "reimport_url=/api/v1/cad/files/file-5/bom/reimport" in readme
    assert "mismatch_status=mismatch" in readme
    assert "proof_manifest_file=proof_manifest.json" in readme


def test_export_cad_bom_bundle_json_supports_job_fallback():
    file_container = SimpleNamespace(
        id="file-6",
        filename="assy2.step",
        cad_bom_path=None,
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="approved",
        cad_review_note="accepted",
        cad_review_by_id=11,
        cad_reviewed_at=datetime(2026, 3, 22, 11, 0, 0),
    )
    client = _cad_client(
        file_container=file_container,
        jobs=[
            SimpleNamespace(
                id="job-6",
                status="completed",
                created_at=datetime(2026, 3, 22, 8, 0, 0),
                completed_at=datetime(2026, 3, 22, 8, 5, 0),
                payload={
                    "file_id": "file-6",
                    "item_id": "item-6",
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
                        "bom": {
                            "root": {"id": "assy-root", "children": [{"id": "child-1"}]},
                        },
                    },
                },
            )
        ],
        history_logs=[],
    )

    with patch(
        "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
        return_value=_sample_mismatch(status="match"),
    ):
        response = client.get("/api/v1/cad/files/file-6/bom/export?export_format=json")

    assert response.status_code == 200
    body = response.json()
    assert body["file"]["file_id"] == "file-6"
    assert body["file"]["has_stored_artifact"] is False
    assert body["cad_bom"]["job_id"] == "job-6"
    assert body["cad_bom"]["summary"]["status"] == "ready"
    assert body["cad_bom"]["mismatch"]["status"] == "match"
    assert body["proof_manifest"]["mismatch_status"] == "match"
    assert body["review"]["state"] == "approved"
    assert body["links"]["raw_bom_url"] is None


def test_export_cad_bom_bundle_rejects_unsupported_format():
    file_container = SimpleNamespace(
        id="file-7",
        filename="assy3.step",
        cad_bom_path="/vault/file-7.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state=None,
        cad_review_note=None,
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    client = _cad_client(file_container=file_container)
    stored_payload = {
        "file_id": "file-7",
        "item_id": "item-7",
        "import_result": {"ok": True, "contract_validation": {"status": "valid", "issues": []}},
        "bom": {"nodes": [], "edges": []},
    }

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(status="match"),
        ):
            def _download(_path, output_stream):
                output_stream.write(json.dumps(stored_payload).encode("utf-8"))

            file_service_cls.return_value.download_file.side_effect = _download
            response = client.get("/api/v1/cad/files/file-7/bom/export?export_format=xlsx")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported export format"
