from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db


def _client_with_user(user):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), mock_db_session


def test_workorder_doc_export_pdf_returns_pdf_payload():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkorderDocumentPackService"
    ) as service_cls:
        service_cls.return_value.export_pack.return_value = {
            "manifest": {
                "generated_at": "2026-02-28T00:00:00Z",
                "routing_id": "r-1",
                "operation_id": "op-1",
                "count": 1,
                "documents": [
                    {
                        "document_item_id": "doc-1",
                        "operation_id": "op-1",
                        "inherit_to_children": True,
                        "visible_in_production": True,
                    }
                ],
            },
            "zip_bytes": b"PK\x03\x04",
        }
        resp = client.get(
            "/api/v1/workorder-docs/export?routing_id=r-1&operation_id=op-1&export_format=pdf"
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/pdf")
    assert 'filename="workorder-doc-pack.pdf"' in (
        resp.headers.get("content-disposition", "")
    )
    assert resp.content.startswith(b"%PDF")


def test_workorder_doc_export_rejects_unknown_format():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.WorkorderDocumentPackService"
    ) as service_cls:
        service_cls.return_value.export_pack.return_value = {
            "manifest": {"routing_id": "r-1", "documents": [], "count": 0},
            "zip_bytes": b"PK\x03\x04",
        }
        resp = client.get(
            "/api/v1/workorder-docs/export?routing_id=r-1&export_format=xlsx"
        )

    assert resp.status_code == 400
    assert "export_format" in (resp.json().get("detail") or "")


def test_breakage_helpdesk_sync_endpoint_returns_job():
    user = SimpleNamespace(id=3, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.BreakageIncidentService"
    ) as service_cls:
        service_cls.return_value.enqueue_helpdesk_stub_sync.return_value = SimpleNamespace(
            id="job-1",
            task_type="breakage_helpdesk_sync_stub",
            status="pending",
            created_at=None,
        )
        resp = client.post(
            "/api/v1/breakages/inc-1/helpdesk-sync",
            json={"metadata_json": {"channel": "qa"}},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == "inc-1"
    assert data["job_id"] == "job-1"
    assert data["task_type"] == "breakage_helpdesk_sync_stub"
    assert db.commit.called


def test_doc_sync_create_job_maps_missing_site_to_404():
    user = SimpleNamespace(id=5, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.DocumentMultiSiteService"
    ) as service_cls:
        service_cls.return_value.enqueue_sync.side_effect = ValueError(
            "Remote site not found: s-404"
        )
        resp = client.post(
            "/api/v1/doc-sync/jobs",
            json={
                "site_id": "s-404",
                "direction": "push",
                "document_ids": ["d-1"],
            },
        )

    assert resp.status_code == 404


def test_3d_overlay_component_permission_denied_maps_403():
    user = SimpleNamespace(id=8, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.parallel_tasks_router.ThreeDOverlayService"
    ) as service_cls:
        service_cls.return_value.resolve_component.side_effect = PermissionError(
            "Overlay is not visible for current roles"
        )
        resp = client.get(
            "/api/v1/cad-3d/overlays/doc-1/components/C-001"
        )

    assert resp.status_code == 403
