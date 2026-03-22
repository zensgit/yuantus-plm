import json
import io
import zipfile
from datetime import datetime, timezone
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


def _sample_asset_quality(
    *,
    status="ok",
    result_status="complete",
    converter_status="ok",
    issue_codes=None,
    recovery_actions=None,
):
    return {
        "status": status,
        "result_status": result_status,
        "geometry_format": "gltf",
        "schema_version": 7,
        "result": {
            "status": converter_status,
            "conversion_status": "completed",
            "error_output": None,
            "warnings": [],
        },
        "bbox": [0, 0, 0, 10, 20, 30],
        "bbox_source": "mesh_metadata",
        "triangle_count": 420,
        "entity_count": 12,
        "lod": {
            "status": "available",
            "source": "mesh_metadata",
            "count": 2,
            "levels": ["0", "1"],
            "files": {},
        },
        "proof_files": ["mesh.gltf", "mesh.bin", "mesh_metadata.json"],
        "issue_codes": issue_codes or [],
        "recovery_actions": recovery_actions or [],
        "links": {
            "geometry_url": "/api/v1/file/file-1/geometry",
            "manifest_url": "/api/v1/file/file-1/cad_manifest",
            "document_url": "/api/v1/file/file-1/cad_document",
            "metadata_url": "/api/v1/file/file-1/cad_metadata",
            "viewer_readiness_url": "/api/v1/file/file-1/viewer_readiness",
            "asset_quality_url": "/api/v1/file/file-1/asset_quality",
        },
    }


def _sample_viewer_readiness(*, asset_quality=None, viewer_mode="full", is_viewer_ready=True):
    return {
        "viewer_mode": viewer_mode,
        "geometry_available": True,
        "manifest_available": True,
        "preview_available": False,
        "available_assets": ["mesh.gltf", "mesh.bin"],
        "geometry_format": "gltf",
        "schema_version": 7,
        "conversion_status": "completed",
        "blocking_reasons": [] if is_viewer_ready else ["conversion_pending"],
        "asset_quality": asset_quality or _sample_asset_quality(),
        "is_viewer_ready": is_viewer_ready,
    }


def _cad_client(
    *,
    file_container,
    jobs=None,
    item_file_rows=None,
    history_logs=None,
    return_db=False,
):
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
    client = TestClient(app)
    if return_db:
        return client, mock_db
    return client


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


def test_get_cad_operator_proof_returns_linked_asset_quality_and_mismatch_surface():
    file_container = SimpleNamespace(
        id="file-proof-1",
        filename="assy-proof.step",
        cad_bom_path="/vault/file-proof-1.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs proof review",
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    client = _cad_client(
        file_container=file_container,
        history_logs=[
            SimpleNamespace(
                id="log-proof-1",
                action="cad_bom_reimport_requested",
                payload={"job_id": "job-proof-1"},
                created_at=datetime(2026, 3, 22, 9, 30, 0),
                user_id=7,
            )
        ],
    )
    stored_payload = {
        "file_id": "file-proof-1",
        "item_id": "item-proof-1",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }
    asset_quality = _sample_asset_quality(
        status="degraded",
        result_status="complete",
        converter_status="degraded",
        issue_codes=["conversion_result_degraded"],
        recovery_actions=[
            {"code": "inspect_converter_result", "label": "Inspect converter result."}
        ],
    )
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=asset_quality,
        viewer_mode="full",
        is_viewer_ready=True,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=1,
                updates=1,
                issue_codes=["live_bom_quantity_mismatch"],
                recovery_actions=[
                    {"code": "review_live_bom_quantities", "label": "Review quantities."}
                ],
                risk_level="medium",
            ),
        ):
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                def _download(_path, output_stream):
                    output_stream.write(json.dumps(stored_payload).encode("utf-8"))

                file_service_cls.return_value.download_file.side_effect = _download
                response = client.get("/api/v1/cad/files/file-proof-1/proof")

    assert response.status_code == 200
    body = response.json()
    assert body["asset_quality"]["status"] == "degraded"
    assert body["viewer_readiness"]["viewer_mode"] == "full"
    assert body["cad_bom"]["mismatch"]["status"] == "mismatch"
    assert body["operator_proof"]["status"] == "needs_review"
    assert body["operator_proof"]["decision_status"] == "open"
    assert body["operator_proof"]["requires_operator_decision"] is True
    assert "asset_quality_degraded" in body["operator_proof"]["proof_gaps"]
    assert "cad_bom_live_mismatch" in body["operator_proof"]["proof_gaps"]
    assert body["links"]["proof_url"] == "/api/v1/cad/files/file-proof-1/proof?history_limit=20"
    assert (
        body["links"]["proof_decisions_url"]
        == "/api/v1/cad/files/file-proof-1/proof/decisions?history_limit=20"
    )
    assert body["proof_manifest"]["bundle_kind"] == "cad_operator_proof_bundle"
    assert body["proof_manifest"]["decision_status"] == "open"
    assert body["proof_decisions"] == []
    assert body["active_decision"] is None


def test_get_cad_operator_proof_returns_active_waiver_for_current_fingerprint():
    file_container = SimpleNamespace(
        id="file-proof-2",
        filename="assy-proof.step",
        cad_bom_path="/vault/file-proof-2.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs proof review",
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    stored_payload = {
        "file_id": "file-proof-2",
        "item_id": "item-proof-2",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }
    asset_quality = _sample_asset_quality(
        status="degraded",
        result_status="complete",
        converter_status="degraded",
        issue_codes=["conversion_result_degraded"],
    )
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=asset_quality,
        viewer_mode="full",
        is_viewer_ready=True,
    )
    mismatch = _sample_mismatch(
        status="mismatch",
        total_ops=1,
        updates=1,
        issue_codes=["live_bom_quantity_mismatch"],
        risk_level="medium",
    )
    history_client = _cad_client(
        file_container=file_container,
        history_logs=[
            SimpleNamespace(
                id="log-proof-waiver",
                action="cad_operator_proof_waived",
                payload={
                    "decision": "waived",
                    "scope": "full_proof",
                    "comment": "accepted during staged rollout",
                    "reason_code": "pilot_rollout",
                    "issue_codes": [
                        "conversion_result_degraded",
                        "asset_quality_degraded",
                        "live_bom_quantity_mismatch",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "proof_fingerprint": "proof-fp-1",
                    "proof_status": "needs_review",
                    "proof_gaps": [
                        "asset_quality_degraded",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "asset_quality_status": "degraded",
                    "mismatch_status": "mismatch",
                    "review_state": "pending",
                },
                created_at=datetime(2026, 3, 22, 10, 0, 0),
                user_id=9,
            )
        ],
    )
    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=mismatch,
        ):
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                with patch(
                    "yuantus.meta_engine.web.cad_router._compute_operator_proof_fingerprint",
                    return_value="proof-fp-1",
                ):
                    file_service_cls.return_value.download_file.side_effect = (
                        lambda _path, output_stream: output_stream.write(
                            json.dumps(stored_payload).encode("utf-8")
                        )
                    )
                    response = history_client.get("/api/v1/cad/files/file-proof-2/proof")

    assert response.status_code == 200
    body = response.json()
    assert body["operator_proof"]["decision_status"] == "waived"
    assert body["operator_proof"]["decision_validity_status"] == "missing_expiry"
    assert body["operator_proof"]["decision_renewal_required"] is True
    assert body["operator_proof"]["requires_operator_decision"] is True
    assert body["active_decision"]["decision"] == "waived"
    assert body["active_decision"]["reason_code"] == "pilot_rollout"
    assert body["active_decision"]["covers_current_proof"] is True
    assert body["proof_manifest"]["active_decision_status"] == "waived"
    assert body["proof_manifest"]["active_decision_covers_current_proof"] is True


def test_get_cad_operator_proof_marks_expired_waiver_for_renewal():
    file_container = SimpleNamespace(
        id="file-proof-expired",
        filename="assy-proof.step",
        cad_bom_path="/vault/file-proof-expired.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs proof review",
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    stored_payload = {
        "file_id": "file-proof-expired",
        "item_id": "item-proof-expired",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=_sample_asset_quality(
            status="degraded",
            result_status="complete",
            converter_status="degraded",
            issue_codes=["conversion_result_degraded"],
        ),
        viewer_mode="full",
        is_viewer_ready=True,
    )
    client = _cad_client(
        file_container=file_container,
        history_logs=[
            SimpleNamespace(
                id="log-proof-expired",
                action="cad_operator_proof_waived",
                payload={
                    "decision": "waived",
                    "scope": "full_proof",
                    "comment": "temporary waiver expired",
                    "reason_code": "pilot_rollout",
                    "issue_codes": [
                        "conversion_result_degraded",
                        "asset_quality_degraded",
                        "live_bom_quantity_mismatch",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "proof_fingerprint": "proof-fp-expired",
                    "proof_status": "needs_review",
                    "proof_gaps": [
                        "asset_quality_degraded",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "asset_quality_status": "degraded",
                    "mismatch_status": "mismatch",
                    "review_state": "pending",
                    "expires_at": "2026-03-20T12:00:00+00:00",
                },
                created_at=datetime(2026, 3, 20, 8, 0, 0),
                user_id=9,
            )
        ],
    )
    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=1,
                updates=1,
                issue_codes=["live_bom_quantity_mismatch"],
                risk_level="medium",
            ),
        ):
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                with patch(
                    "yuantus.meta_engine.web.cad_router._compute_operator_proof_fingerprint",
                    return_value="proof-fp-expired",
                ):
                    with patch(
                        "yuantus.meta_engine.web.cad_router._utc_now",
                        return_value=datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc),
                    ):
                        file_service_cls.return_value.download_file.side_effect = (
                            lambda _path, output_stream: output_stream.write(
                                json.dumps(stored_payload).encode("utf-8")
                            )
                        )
                        response = client.get("/api/v1/cad/files/file-proof-expired/proof")

    assert response.status_code == 200
    body = response.json()
    assert body["operator_proof"]["decision_status"] == "waived"
    assert body["operator_proof"]["decision_validity_status"] == "expired"
    assert body["operator_proof"]["decision_renewal_required"] is True
    assert body["operator_proof"]["requires_operator_decision"] is True
    action_codes = [row["code"] for row in body["operator_proof"]["next_actions"]]
    assert "renew_operator_proof_decision" in action_codes
    assert body["active_decision"]["validity_status"] == "expired"
    assert body["proof_manifest"]["decision_validity_status"] == "expired"
    assert body["proof_manifest"]["decision_renewal_required"] is True


def test_get_cad_operator_proof_decisions_returns_current_entries():
    file_container = SimpleNamespace(
        id="file-proof-2b",
        filename="assy-proof.step",
        cad_bom_path="/vault/file-proof-2b.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs proof review",
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    stored_payload = {
        "file_id": "file-proof-2b",
        "item_id": "item-proof-2b",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=_sample_asset_quality(
            status="degraded",
            result_status="complete",
            converter_status="degraded",
            issue_codes=["conversion_result_degraded"],
        ),
        viewer_mode="full",
        is_viewer_ready=True,
    )
    client = _cad_client(
        file_container=file_container,
        history_logs=[
            SimpleNamespace(
                id="log-proof-ack",
                action="cad_operator_proof_acknowledged",
                payload={
                    "decision": "acknowledged",
                    "scope": "full_proof",
                    "comment": "accepted for support handoff",
                    "reason_code": "support_handoff",
                    "issue_codes": [
                        "conversion_result_degraded",
                        "asset_quality_degraded",
                        "live_bom_quantity_mismatch",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "proof_fingerprint": "proof-fp-2b",
                    "proof_status": "needs_review",
                    "proof_gaps": [
                        "asset_quality_degraded",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "asset_quality_status": "degraded",
                    "mismatch_status": "mismatch",
                    "review_state": "pending",
                    "expires_at": "2026-03-24T12:00:00+00:00",
                },
                created_at=datetime(2026, 3, 22, 10, 15, 0),
                user_id=9,
            )
        ],
    )
    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=1,
                updates=1,
                issue_codes=["live_bom_quantity_mismatch"],
                risk_level="medium",
            ),
        ):
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                with patch(
                    "yuantus.meta_engine.web.cad_router._compute_operator_proof_fingerprint",
                    return_value="proof-fp-2b",
                ):
                    with patch(
                        "yuantus.meta_engine.web.cad_router._utc_now",
                        return_value=datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc),
                    ):
                        file_service_cls.return_value.download_file.side_effect = (
                            lambda _path, output_stream: output_stream.write(
                                json.dumps(stored_payload).encode("utf-8")
                            )
                        )
                        response = client.get(
                            "/api/v1/cad/files/file-proof-2b/proof/decisions?history_limit=20"
                        )

    assert response.status_code == 200
    body = response.json()
    assert body["current_fingerprint"] == "proof-fp-2b"
    assert body["active_decision"]["decision"] == "acknowledged"
    assert body["active_decision"]["validity_status"] == "expiring"
    assert body["active_decision"]["renewal_recommended"] is True
    assert body["entries"][0]["decision"] == "acknowledged"
    assert body["entries"][0]["is_current"] is True
    assert body["entries"][0]["covers_current_proof"] is True


def test_record_cad_operator_proof_waiver_requires_expires_at():
    file_container = SimpleNamespace(
        id="file-proof-3b",
        filename="assy-proof.step",
        cad_bom_path="/vault/file-proof-3b.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs proof review",
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    client = _cad_client(file_container=file_container, history_logs=[])
    stored_payload = {
        "file_id": "file-proof-3b",
        "item_id": "item-proof-3b",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=_sample_asset_quality(
            status="degraded",
            result_status="complete",
            converter_status="degraded",
            issue_codes=["conversion_result_degraded"],
        ),
        viewer_mode="full",
        is_viewer_ready=True,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=1,
                updates=1,
                issue_codes=["live_bom_quantity_mismatch"],
                risk_level="medium",
            ),
        ):
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                file_service_cls.return_value.download_file.side_effect = (
                    lambda _path, output_stream: output_stream.write(
                        json.dumps(stored_payload).encode("utf-8")
                    )
                )
                response = client.post(
                    "/api/v1/cad/files/file-proof-3b/proof/decisions",
                    json={
                        "decision": "waived",
                        "scope": "full_proof",
                        "comment": "missing expiry should fail",
                        "reason_code": "downstream_lag",
                    },
                )

    assert response.status_code == 400
    assert response.json()["detail"] == "Proof waiver expires_at is required"


def test_record_cad_operator_proof_decision_logs_current_snapshot():
    file_container = SimpleNamespace(
        id="file-proof-3",
        filename="assy-proof.step",
        cad_bom_path="/vault/file-proof-3.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs proof review",
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    client, mock_db = _cad_client(
        file_container=file_container,
        history_logs=[],
        return_db=True,
    )
    stored_payload = {
        "file_id": "file-proof-3",
        "item_id": "item-proof-3",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }
    asset_quality = _sample_asset_quality(
        status="degraded",
        result_status="complete",
        converter_status="degraded",
        issue_codes=["conversion_result_degraded"],
    )
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=asset_quality,
        viewer_mode="full",
        is_viewer_ready=True,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=1,
                updates=1,
                issue_codes=["live_bom_quantity_mismatch"],
                risk_level="medium",
            ),
        ):
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                with patch(
                    "yuantus.meta_engine.web.cad_router._compute_operator_proof_fingerprint",
                    return_value="proof-fp-ack-1",
                ):
                    file_service_cls.return_value.download_file.side_effect = (
                        lambda _path, output_stream: output_stream.write(
                            json.dumps(stored_payload).encode("utf-8")
                        )
                    )
                    response = client.post(
                        "/api/v1/cad/files/file-proof-3/proof/decisions",
                        json={
                            "decision": "waived",
                            "scope": "full_proof",
                            "comment": "accepted while downstream live BOM catches up",
                            "reason_code": "downstream_lag",
                            "issue_codes": [
                                "conversion_result_degraded",
                                "live_bom_quantity_mismatch",
                                "asset_quality_degraded",
                                "cad_bom_live_mismatch",
                                "cad_review_pending",
                            ],
                            "expires_at": "2026-03-29T12:00:00Z",
                        },
                    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "waived"
    assert body["proof_fingerprint"] == "proof-fp-ack-1"
    assert body["covers_current_proof"] is True
    logged_entry = next(
        call.args[0]
        for call in mock_db.add.call_args_list
        if getattr(call.args[0], "action", None) == "cad_operator_proof_waived"
    )
    assert logged_entry.action == "cad_operator_proof_waived"
    assert logged_entry.payload["reason_code"] == "downstream_lag"
    assert logged_entry.payload["proof_fingerprint"] == "proof-fp-ack-1"
    assert logged_entry.payload["proof_status"] == "needs_review"
    assert logged_entry.payload["links"]["proof_decisions_url"].endswith(
        "/api/v1/cad/files/file-proof-3/proof/decisions?history_limit=50"
    )
    mock_db.commit.assert_called_once()


def test_record_cad_operator_proof_decision_renewal_logs_renewed_action():
    file_container = SimpleNamespace(
        id="file-proof-renew",
        filename="assy-proof.step",
        cad_bom_path="/vault/file-proof-renew.json",
        cad_connector_id="step",
        cad_format="STEP",
        document_type="3d",
        cad_review_state="pending",
        cad_review_note="needs proof review",
        cad_review_by_id=None,
        cad_reviewed_at=None,
    )
    client, mock_db = _cad_client(
        file_container=file_container,
        history_logs=[
            SimpleNamespace(
                id="log-proof-renew-1",
                action="cad_operator_proof_waived",
                payload={
                    "decision": "waived",
                    "scope": "full_proof",
                    "comment": "temporary waiver",
                    "reason_code": "pilot_rollout",
                    "issue_codes": [
                        "conversion_result_degraded",
                        "live_bom_quantity_mismatch",
                        "asset_quality_degraded",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "proof_fingerprint": "proof-fp-renew-1",
                    "proof_status": "needs_review",
                    "proof_gaps": [
                        "asset_quality_degraded",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "asset_quality_status": "degraded",
                    "mismatch_status": "mismatch",
                    "review_state": "pending",
                    "expires_at": "2026-03-24T12:00:00+00:00",
                },
                created_at=datetime(2026, 3, 22, 9, 0, 0),
                user_id=9,
            )
        ],
        return_db=True,
    )
    stored_payload = {
        "file_id": "file-proof-renew",
        "item_id": "item-proof-renew",
        "imported_at": "2026-03-22T09:00:00Z",
        "import_result": {"ok": True},
        "bom": {"nodes": [{"id": "assy-root"}], "edges": [], "root": "assy-root"},
    }
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=_sample_asset_quality(
            status="degraded",
            result_status="complete",
            converter_status="degraded",
            issue_codes=["conversion_result_degraded"],
        ),
        viewer_mode="full",
        is_viewer_ready=True,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls:
        with patch(
            "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
            return_value=_sample_mismatch(
                status="mismatch",
                total_ops=1,
                updates=1,
                issue_codes=["live_bom_quantity_mismatch"],
                risk_level="medium",
            ),
        ):
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                with patch(
                    "yuantus.meta_engine.web.cad_router._compute_operator_proof_fingerprint",
                    return_value="proof-fp-renew-1",
                ):
                    with patch(
                        "yuantus.meta_engine.web.cad_router._utc_now",
                        return_value=datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc),
                    ):
                        file_service_cls.return_value.download_file.side_effect = (
                            lambda _path, output_stream: output_stream.write(
                                json.dumps(stored_payload).encode("utf-8")
                            )
                        )
                        response = client.post(
                            "/api/v1/cad/files/file-proof-renew/proof/decisions",
                            json={
                                "decision": "waived",
                                "scope": "full_proof",
                                "comment": "extended waiver after supplier confirmation",
                                "reason_code": "supplier_hold",
                                "renew_from_decision_id": "log-proof-renew-1",
                                "issue_codes": [
                                    "conversion_result_degraded",
                                    "live_bom_quantity_mismatch",
                                    "asset_quality_degraded",
                                    "cad_bom_live_mismatch",
                                    "cad_review_pending",
                                ],
                                "expires_at": "2026-04-02T12:00:00Z",
                            },
                        )

    assert response.status_code == 200
    body = response.json()
    assert body["audit_action"] == "cad_operator_proof_waiver_renewed"
    assert body["renewed_from_decision_id"] == "log-proof-renew-1"
    assert body["validity_status"] == "active"
    logged_entry = next(
        call.args[0]
        for call in mock_db.add.call_args_list
        if getattr(call.args[0], "action", None) == "cad_operator_proof_waiver_renewed"
    )
    assert logged_entry.payload["renewed_from_decision_id"] == "log-proof-renew-1"
    assert logged_entry.payload["expires_at"] == "2026-04-02T12:00:00+00:00"
    mock_db.commit.assert_called_once()


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
            ),
            SimpleNamespace(
                id="log-2",
                action="cad_operator_proof_acknowledged",
                payload={
                    "decision": "acknowledged",
                    "scope": "full_proof",
                    "comment": "tracked in rollout checklist",
                    "reason_code": "rollout_tracking",
                    "issue_codes": [
                        "conversion_result_degraded",
                        "mesh_stats_missing",
                        "live_bom_structure_mismatch",
                        "live_bom_quantity_mismatch",
                        "asset_quality_degraded",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "proof_fingerprint": "proof-fp-export-1",
                    "proof_status": "needs_review",
                    "proof_gaps": [
                        "asset_quality_degraded",
                        "cad_bom_live_mismatch",
                        "cad_review_pending",
                    ],
                    "asset_quality_status": "degraded",
                    "mismatch_status": "mismatch",
                    "review_state": "pending",
                },
                created_at=datetime(2026, 3, 22, 9, 45, 0),
                user_id=9,
            ),
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
    asset_quality = _sample_asset_quality(
        status="degraded",
        result_status="partial",
        converter_status="degraded",
        issue_codes=["conversion_result_degraded", "mesh_stats_missing"],
        recovery_actions=[
            {"code": "inspect_converter_result", "label": "Inspect converter result."},
            {"code": "inspect_mesh_metadata_output", "label": "Inspect mesh metadata."},
        ],
    )
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=asset_quality,
        viewer_mode="full",
        is_viewer_ready=True,
    )

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
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=viewer_readiness,
            ):
                with patch(
                    "yuantus.meta_engine.web.cad_router._compute_operator_proof_fingerprint",
                    return_value="proof-fp-export-1",
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
    assert "operator_proof.json" in names
    assert "active_decision.json" in names
    assert "proof_decisions.json" in names
    assert "proof_decisions.csv" in names
    assert "viewer_readiness.json" in names
    assert "asset_quality.json" in names
    assert "asset_quality_issue_codes.csv" in names
    assert "asset_quality_recovery_actions.csv" in names
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
    assert bundle["asset_quality"]["status"] == "degraded"
    assert bundle["viewer_readiness"]["viewer_mode"] == "full"
    assert bundle["cad_bom"]["summary"]["status"] == "degraded"
    assert bundle["cad_bom"]["mismatch"]["status"] == "mismatch"
    assert bundle["operator_proof"]["status"] == "needs_review"
    assert bundle["operator_proof"]["decision_status"] == "acknowledged"
    assert bundle["operator_proof"]["decision_validity_status"] == "no_expiry"
    assert bundle["proof_manifest"]["bundle_kind"] == "cad_operator_proof_bundle"
    assert bundle["proof_manifest"]["operator_proof_status"] == "needs_review"
    assert bundle["proof_manifest"]["decision_status"] == "acknowledged"
    assert bundle["proof_manifest"]["decision_validity_status"] == "no_expiry"
    assert bundle["proof_manifest"]["active_decision_status"] == "acknowledged"
    assert bundle["proof_manifest"]["asset_quality_status"] == "degraded"
    assert bundle["proof_manifest"]["mismatch_grouped_counters"]["structure"] == 1
    assert bundle["proof_manifest"]["mismatch_line_key"] == "child_id_find_refdes"
    assert bundle["proof_manifest"]["proof_files"][-1] == "README.txt"
    assert bundle["active_decision"]["decision"] == "acknowledged"
    assert bundle["history"][0]["action"] == "cad_bom_reimport_requested"

    history_csv = zf.read("history.csv").decode("utf-8-sig")
    assert history_csv.splitlines()[0] == "id,action,created_at,user_id,payload"
    assert "cad_bom_reimport_requested" in history_csv

    readme = zf.read("README.txt").decode("utf-8")
    assert "structured_bom_url=/api/v1/cad/files/file-5/bom" in readme
    assert "mismatch_url=/api/v1/cad/files/file-5/bom/mismatch" in readme
    assert "proof_url=/api/v1/cad/files/file-5/proof?history_limit=20" in readme
    assert "proof_decisions_url=/api/v1/cad/files/file-5/proof/decisions?history_limit=20" in readme
    assert "asset_quality_url=/api/v1/file/file-5/asset_quality" in readme
    assert "viewer_readiness_url=/api/v1/file/file-5/viewer_readiness" in readme
    assert "reimport_url=/api/v1/cad/files/file-5/bom/reimport" in readme
    assert "operator_proof_status=needs_review" in readme
    assert "decision_status=acknowledged" in readme
    assert "decision_validity_status=no_expiry" in readme
    assert "asset_quality_status=degraded" in readme
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
    viewer_readiness = _sample_viewer_readiness(
        asset_quality=_sample_asset_quality(),
        viewer_mode="full",
        is_viewer_ready=True,
    )

    with patch(
        "yuantus.meta_engine.web.cad_router.build_cad_bom_mismatch_analysis",
        return_value=_sample_mismatch(status="match"),
    ):
        with patch(
            "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
            return_value=viewer_readiness,
        ):
            response = client.get("/api/v1/cad/files/file-6/bom/export?export_format=json")

    assert response.status_code == 200
    body = response.json()
    assert body["file"]["file_id"] == "file-6"
    assert body["file"]["has_stored_artifact"] is False
    assert body["viewer_readiness"]["viewer_mode"] == "full"
    assert body["asset_quality"]["status"] == "ok"
    assert body["cad_bom"]["job_id"] == "job-6"
    assert body["cad_bom"]["summary"]["status"] == "ready"
    assert body["cad_bom"]["mismatch"]["status"] == "match"
    assert body["operator_proof"]["status"] == "ready"
    assert body["operator_proof"]["decision_status"] == "not_required"
    assert body["proof_manifest"]["bundle_kind"] == "cad_operator_proof_bundle"
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
            with patch(
                "yuantus.meta_engine.web.cad_router.CADConverterService.assess_viewer_readiness",
                return_value=_sample_viewer_readiness(
                    asset_quality=_sample_asset_quality(),
                    viewer_mode="full",
                    is_viewer_ready=True,
                ),
            ):
                def _download(_path, output_stream):
                    output_stream.write(json.dumps(stored_payload).encode("utf-8"))

                file_service_cls.return_value.download_file.side_effect = _download
                response = client.get("/api/v1/cad/files/file-7/bom/export?export_format=xlsx")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported export format"
