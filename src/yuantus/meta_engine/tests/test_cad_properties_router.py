from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_properties_router import cad_properties_router


class _FakeDb:
    def __init__(self, *, file_container=None):
        self.file_container = file_container
        self.add = MagicMock()
        self.commit = MagicMock()

    def get(self, model, identity):
        if model is FileContainer and self.file_container is not None:
            if getattr(self.file_container, "id", None) == identity:
                return self.file_container
        return None


def _client(file_container=None) -> tuple[TestClient, _FakeDb]:
    db = _FakeDb(file_container=file_container)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_properties_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=7,
        roles=["engineer"],
        is_superuser=False,
        tenant_id="tenant-1",
        org_id="org-1",
    )
    return TestClient(app), db


def _file(**overrides):
    values = {
        "id": "file-1",
        "cad_properties": None,
        "cad_properties_source": None,
        "cad_properties_updated_at": None,
        "cad_document_schema_version": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_get_cad_properties_returns_existing_properties() -> None:
    client, _db = _client(
        file_container=_file(
            cad_properties={"material": "AL-6061"},
            cad_properties_source="imported",
            cad_properties_updated_at=datetime(2026, 4, 22, 10, 0, 0),
            cad_document_schema_version=3,
        )
    )

    response = client.get("/api/v1/cad/files/file-1/properties")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "properties": {"material": "AL-6061"},
        "updated_at": "2026-04-22T10:00:00",
        "source": "imported",
        "cad_document_schema_version": 3,
    }


def test_get_cad_properties_returns_empty_defaults() -> None:
    client, _db = _client(file_container=_file())

    response = client.get("/api/v1/cad/files/file-1/properties")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "properties": {},
        "updated_at": None,
        "source": None,
        "cad_document_schema_version": None,
    }


def test_get_cad_properties_returns_404_when_file_missing() -> None:
    client, _db = _client(file_container=None)

    response = client.get("/api/v1/cad/files/file-1/properties")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_patch_cad_properties_updates_file_and_logs_change() -> None:
    file_container = _file(cad_document_schema_version=4)
    client, db = _client(file_container=file_container)

    response = client.patch(
        "/api/v1/cad/files/file-1/properties",
        json={
            "properties": {"material": "AL-7075", "finish": "hard-anodized"},
            "source": "manual",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == "file-1"
    assert body["properties"] == {"material": "AL-7075", "finish": "hard-anodized"}
    assert body["source"] == "manual"
    assert body["cad_document_schema_version"] == 4
    assert isinstance(body["updated_at"], str)
    assert file_container.cad_properties == {
        "material": "AL-7075",
        "finish": "hard-anodized",
    }
    assert file_container.cad_properties_source == "manual"
    assert db.commit.call_count == 1
    added = [call.args[0] for call in db.add.call_args_list]
    assert file_container in added
    audit_entries = [item for item in added if isinstance(item, CadChangeLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].file_id == "file-1"
    assert audit_entries[0].action == "cad_properties_update"
    assert audit_entries[0].payload == {
        "properties": {"material": "AL-7075", "finish": "hard-anodized"},
        "source": "manual",
    }
    assert audit_entries[0].tenant_id == "tenant-1"
    assert audit_entries[0].org_id == "org-1"
    assert audit_entries[0].user_id == 7


def test_patch_cad_properties_defaults_blank_source_to_manual() -> None:
    file_container = _file()
    client, _db = _client(file_container=file_container)

    response = client.patch(
        "/api/v1/cad/files/file-1/properties",
        json={"properties": {"mass": 12.3}, "source": "  "},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "manual"
    assert file_container.cad_properties_source == "manual"


def test_patch_cad_properties_returns_404_when_file_missing() -> None:
    client, _db = _client(file_container=None)

    response = client.patch(
        "/api/v1/cad/files/file-1/properties",
        json={"properties": {"material": "AL-7075"}},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
