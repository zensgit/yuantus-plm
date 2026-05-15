"""Behavior tests for /workorder-docs router R1 fields.

Covers POST round-trip of document_version_id (including the legacy payload
preservation path), and GET /workorder-docs/export `require_locked_versions`
plumbing + 409 mapping.

The router contract tests in
``test_parallel_tasks_workorder_docs_router_contracts`` cover route shape;
this file covers behavior wiring.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.meta_engine.web.parallel_tasks_workorder_docs_router import (
    parallel_tasks_workorder_docs_router,
)


def _client_with_mocks():
    from yuantus.api.dependencies.auth import get_current_user
    from yuantus.database import get_db

    mock_db = MagicMock()
    user = SimpleNamespace(id=42, email="op@example.com", roles=["operator"])

    app = FastAPI()
    app.include_router(parallel_tasks_workorder_docs_router, prefix="/api/v1")

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), mock_db


def _fake_link(**overrides):
    base = dict(
        id="link-1",
        routing_id="r-1",
        operation_id=None,
        document_item_id="doc-1",
        inherit_to_children=True,
        visible_in_production=True,
        document_version_id="v-1",
        version_locked_at=None,
        version_lock_source="manual",
        created_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _serialized(link, *, version_locked: bool = True) -> dict:
    return {
        "id": link.id,
        "routing_id": link.routing_id,
        "operation_id": link.operation_id,
        "document_item_id": link.document_item_id,
        "inherit_to_children": link.inherit_to_children,
        "visible_in_production": link.visible_in_production,
        "document_scope": "routing" if link.operation_id is None else "operation",
        "created_at": None,
        "document_version_id": link.document_version_id,
        "version_locked": version_locked,
        "version_lock_source": link.version_lock_source,
        "version_locked_at": None,
        "version_label": "1.A",
        "version_is_current": True,
        "version_is_released": False,
        "version_belongs_to_item": True,
    }


_SVC = "yuantus.meta_engine.web.parallel_tasks_workorder_docs_router.WorkorderDocumentPackService"


def test_post_workorder_doc_link_passes_document_version_id_through():
    client, _db = _client_with_mocks()
    link = _fake_link()
    with patch(_SVC) as svc_cls:
        svc_cls.return_value.upsert_link.return_value = link
        svc_cls.return_value.serialize_link.return_value = _serialized(link)
        resp = client.post(
            "/api/v1/workorder-docs/links",
            json={
                "routing_id": "r-1",
                "document_item_id": "doc-1",
                "document_version_id": "v-1",
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["document_version_id"] == "v-1"
    assert body["version_locked"] is True
    assert body["version_lock_source"] == "manual"

    call_kwargs = svc_cls.return_value.upsert_link.call_args.kwargs
    assert call_kwargs["document_version_id"] == "v-1"


def test_post_workorder_doc_link_omitted_version_field_not_forwarded():
    """Legacy payload (no document_version_id key) must NOT touch the lock."""
    client, _db = _client_with_mocks()
    link = _fake_link(document_version_id=None, version_lock_source=None)
    serialized = _serialized(link, version_locked=False)
    serialized["version_lock_source"] = None
    serialized["version_is_current"] = None
    serialized["version_is_released"] = None
    serialized["version_belongs_to_item"] = None
    serialized["version_label"] = None

    with patch(_SVC) as svc_cls:
        svc_cls.return_value.upsert_link.return_value = link
        svc_cls.return_value.serialize_link.return_value = serialized
        resp = client.post(
            "/api/v1/workorder-docs/links",
            json={"routing_id": "r-1", "document_item_id": "doc-1"},
        )

    assert resp.status_code == 200
    call_kwargs = svc_cls.return_value.upsert_link.call_args.kwargs
    assert "document_version_id" not in call_kwargs


def test_post_workorder_doc_link_explicit_null_forwarded_to_clear():
    client, _db = _client_with_mocks()
    link = _fake_link(document_version_id=None, version_lock_source=None)
    serialized = _serialized(link, version_locked=False)
    serialized["version_lock_source"] = None

    with patch(_SVC) as svc_cls:
        svc_cls.return_value.upsert_link.return_value = link
        svc_cls.return_value.serialize_link.return_value = serialized
        resp = client.post(
            "/api/v1/workorder-docs/links",
            json={
                "routing_id": "r-1",
                "document_item_id": "doc-1",
                "document_version_id": None,
            },
        )

    assert resp.status_code == 200
    call_kwargs = svc_cls.return_value.upsert_link.call_args.kwargs
    assert call_kwargs["document_version_id"] is None


def test_export_passes_require_locked_versions_flag_through():
    client, _db = _client_with_mocks()
    with patch(_SVC) as svc_cls:
        svc_cls.return_value.export_pack.return_value = {
            "manifest": {
                "routing_id": "r-1",
                "operation_id": None,
                "count": 0,
                "documents": [],
                "version_lock_summary": {
                    "locked": 0,
                    "unlocked": 0,
                    "mismatched": 0,
                    "stale": 0,
                    "requires_lock": True,
                },
            },
            "zip_bytes": b"",
        }
        resp = client.get(
            "/api/v1/workorder-docs/export",
            params={
                "routing_id": "r-1",
                "export_format": "json",
                "require_locked_versions": "true",
            },
        )

    assert resp.status_code == 200
    call_kwargs = svc_cls.return_value.export_pack.call_args.kwargs
    assert call_kwargs["require_locked_versions"] is True
    summary = resp.json()["version_lock_summary"]
    assert summary["requires_lock"] is True


def test_export_defaults_require_locked_versions_to_false():
    client, _db = _client_with_mocks()
    with patch(_SVC) as svc_cls:
        svc_cls.return_value.export_pack.return_value = {
            "manifest": {
                "routing_id": "r-1",
                "operation_id": None,
                "count": 0,
                "documents": [],
                "version_lock_summary": {
                    "locked": 0,
                    "unlocked": 0,
                    "mismatched": 0,
                    "stale": 0,
                    "requires_lock": False,
                },
            },
            "zip_bytes": b"",
        }
        resp = client.get(
            "/api/v1/workorder-docs/export",
            params={"routing_id": "r-1", "export_format": "json"},
        )

    assert resp.status_code == 200
    call_kwargs = svc_cls.return_value.export_pack.call_args.kwargs
    assert call_kwargs["require_locked_versions"] is False


def test_export_maps_unlocked_value_error_to_409():
    client, _db = _client_with_mocks()
    with patch(_SVC) as svc_cls:
        svc_cls.return_value.export_pack.side_effect = ValueError(
            "require_locked_versions=true: 1 unlocked + 0 mismatched links "
            "(ids=['link-x'])"
        )
        resp = client.get(
            "/api/v1/workorder-docs/export",
            params={
                "routing_id": "r-1",
                "export_format": "json",
                "require_locked_versions": "true",
            },
        )

    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "workorder_export_unlocked_versions"
    assert "require_locked_versions" in detail["message"]
    assert detail["context"]["require_locked_versions"] is True
    assert detail["context"]["routing_id"] == "r-1"
