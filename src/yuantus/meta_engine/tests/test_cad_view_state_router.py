from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_view_state_router import cad_view_state_router


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


def _user(*, user_id: int = 7):
    return SimpleNamespace(
        id=user_id,
        roles=["engineer"],
        is_superuser=False,
        tenant_id="tenant-1",
        org_id="org-1",
    )


def _client(file_container=None) -> tuple[TestClient, _FakeDb]:
    db = _FakeDb(file_container=file_container)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_view_state_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _user()
    return TestClient(app), db


def _file(**overrides):
    values = {
        "id": "file-1",
        "cad_view_state": None,
        "cad_view_state_source": None,
        "cad_view_state_updated_at": None,
        "cad_document_path": None,
        "cad_document_schema_version": None,
        "is_cad_file": lambda: True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_get_cad_view_state_returns_existing_state() -> None:
    client, _db = _client(
        file_container=_file(
            cad_view_state={
                "hidden_entity_ids": [3, 4],
                "notes": [{"entity_id": 3, "note": "inspect", "color": "red"}],
            },
            cad_view_state_source="client",
            cad_view_state_updated_at=datetime(2026, 4, 22, 10, 0, 0),
            cad_document_schema_version=2,
        )
    )

    response = client.get("/api/v1/cad/files/file-1/view-state")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "hidden_entity_ids": [3, 4],
        "notes": [{"entity_id": 3, "note": "inspect", "color": "red"}],
        "updated_at": "2026-04-22T10:00:00",
        "source": "client",
        "cad_document_schema_version": 2,
    }


def test_get_cad_view_state_returns_empty_defaults() -> None:
    client, _db = _client(file_container=_file())

    response = client.get("/api/v1/cad/files/file-1/view-state")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "hidden_entity_ids": [],
        "notes": [],
        "updated_at": None,
        "source": None,
        "cad_document_schema_version": None,
    }


def test_get_cad_view_state_returns_404_when_file_missing() -> None:
    client, _db = _client(file_container=None)

    response = client.get("/api/v1/cad/files/file-1/view-state")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_patch_cad_view_state_updates_file_and_logs_change() -> None:
    file_container = _file(
        cad_view_state={
            "hidden_entity_ids": [1],
            "notes": [{"entity_id": 1, "note": "old"}],
        },
        cad_view_state_source="client",
    )
    client, db = _client(file_container=file_container)

    response = client.patch(
        "/api/v1/cad/files/file-1/view-state",
        json={
            "hidden_entity_ids": [2],
            "notes": [{"entity_id": 2, "note": "new", "color": "blue"}],
            "source": " manual ",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == "file-1"
    assert body["hidden_entity_ids"] == [2]
    assert body["notes"] == [{"entity_id": 2, "note": "new", "color": "blue"}]
    assert body["source"] == "manual"
    assert isinstance(body["updated_at"], str)
    assert file_container.cad_view_state == {
        "hidden_entity_ids": [2],
        "notes": [{"entity_id": 2, "note": "new", "color": "blue"}],
    }
    assert file_container.cad_view_state_source == "manual"
    assert db.commit.call_count == 1
    added = [call.args[0] for call in db.add.call_args_list]
    assert file_container in added
    audit_entries = [item for item in added if isinstance(item, CadChangeLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].file_id == "file-1"
    assert audit_entries[0].action == "cad_view_state_update"
    assert audit_entries[0].payload == {
        "hidden_entity_ids": [2],
        "notes": [{"entity_id": 2, "note": "new", "color": "blue"}],
        "source": "manual",
        "refresh_preview": False,
    }
    assert audit_entries[0].tenant_id == "tenant-1"
    assert audit_entries[0].org_id == "org-1"
    assert audit_entries[0].user_id == 7


def test_patch_cad_view_state_preserves_existing_fields_when_omitted() -> None:
    file_container = _file(
        cad_view_state={
            "hidden_entity_ids": [5],
            "notes": [{"entity_id": 5, "note": "keep"}],
        },
        cad_view_state_source="client",
    )
    client, _db = _client(file_container=file_container)

    response = client.patch("/api/v1/cad/files/file-1/view-state", json={})

    assert response.status_code == 200
    assert response.json()["hidden_entity_ids"] == [5]
    assert response.json()["notes"] == [{"entity_id": 5, "note": "keep", "color": None}]
    assert response.json()["source"] == "client"


def test_patch_cad_view_state_validates_entity_ids_from_cad_document() -> None:
    file_container = _file(cad_document_path="vault/cad/document.json")
    client, db = _client(file_container=file_container)

    def write_payload(_path, output_stream):
        output_stream.write(b'{"entities": [{"id": 1}]}')

    with patch(
        "yuantus.meta_engine.web.cad_view_state_router.FileService"
    ) as file_service_cls:
        file_service_cls.return_value.download_file.side_effect = write_payload
        response = client.patch(
            "/api/v1/cad/files/file-1/view-state",
            json={"hidden_entity_ids": [2]},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown CAD entity ids: [2]"
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_patch_cad_view_state_refresh_preview_enqueues_preview_job() -> None:
    file_container = _file()
    client, db = _client(file_container=file_container)
    job = SimpleNamespace(id="job-1", task_type="cad_preview", status="pending")

    with patch(
        "yuantus.meta_engine.web.cad_view_state_router.JobService"
    ) as job_service_cls:
        job_service_cls.return_value.create_job.return_value = job
        response = client.patch(
            "/api/v1/cad/files/file-1/view-state",
            json={"hidden_entity_ids": [1], "refresh_preview": True},
        )

    assert response.status_code == 200
    job_service_cls.return_value.create_job.assert_called_once_with(
        task_type="cad_preview",
        payload={
            "file_id": "file-1",
            "tenant_id": "tenant-1",
            "org_id": "org-1",
            "user_id": 7,
        },
        user_id=7,
        priority=15,
        dedupe=True,
    )
    assert db.commit.call_count == 1


def test_patch_cad_view_state_skips_preview_job_for_non_cad_file() -> None:
    file_container = _file(is_cad_file=lambda: False)
    client, _db = _client(file_container=file_container)

    with patch(
        "yuantus.meta_engine.web.cad_view_state_router.JobService"
    ) as job_service_cls:
        response = client.patch(
            "/api/v1/cad/files/file-1/view-state",
            json={"refresh_preview": True},
        )

    assert response.status_code == 200
    job_service_cls.assert_not_called()


def test_patch_cad_view_state_returns_404_when_file_missing() -> None:
    client, _db = _client(file_container=None)

    response = client.patch(
        "/api/v1/cad/files/file-1/view-state",
        json={"hidden_entity_ids": [1]},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
