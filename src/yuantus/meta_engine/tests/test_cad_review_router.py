from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user, require_admin_user
from yuantus.database import get_db
from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_review_router import cad_review_router


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


def _user(*, user_id: int = 7, roles=None, is_superuser: bool = False):
    return SimpleNamespace(
        id=user_id,
        roles=roles or ["engineer"],
        is_superuser=is_superuser,
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
    app.include_router(cad_review_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[require_admin_user] = lambda: _user(
        user_id=1, roles=["admin"], is_superuser=True
    )
    return TestClient(app), db


def _file(**overrides):
    values = {
        "id": "file-1",
        "cad_review_state": None,
        "cad_review_note": None,
        "cad_review_by_id": None,
        "cad_reviewed_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_get_cad_review_returns_existing_state() -> None:
    client, _db = _client(
        file_container=_file(
            cad_review_state="pending",
            cad_review_note="Awaiting review",
            cad_review_by_id=1,
            cad_reviewed_at=datetime(2026, 4, 22, 10, 0, 0),
        )
    )

    response = client.get("/api/v1/cad/files/file-1/review")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "state": "pending",
        "note": "Awaiting review",
        "reviewed_at": "2026-04-22T10:00:00",
        "reviewed_by_id": 1,
    }


def test_get_cad_review_returns_empty_defaults() -> None:
    client, _db = _client(file_container=_file())

    response = client.get("/api/v1/cad/files/file-1/review")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "state": None,
        "note": None,
        "reviewed_at": None,
        "reviewed_by_id": None,
    }


def test_get_cad_review_returns_404_when_file_missing() -> None:
    client, _db = _client(file_container=None)

    response = client.get("/api/v1/cad/files/file-1/review")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_post_cad_review_updates_file_and_logs_change() -> None:
    file_container = _file()
    client, db = _client(file_container=file_container)

    response = client.post(
        "/api/v1/cad/files/file-1/review",
        json={"state": " APPROVED ", "note": "Looks good"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == "file-1"
    assert body["state"] == "approved"
    assert body["note"] == "Looks good"
    assert body["reviewed_by_id"] == 1
    assert isinstance(body["reviewed_at"], str)
    assert file_container.cad_review_state == "approved"
    assert file_container.cad_review_note == "Looks good"
    assert file_container.cad_review_by_id == 1
    assert db.commit.call_count == 1
    added = [call.args[0] for call in db.add.call_args_list]
    assert file_container in added
    audit_entries = [item for item in added if isinstance(item, CadChangeLog)]
    assert len(audit_entries) == 1
    assert audit_entries[0].file_id == "file-1"
    assert audit_entries[0].action == "cad_review_update"
    assert audit_entries[0].payload == {"state": "approved", "note": "Looks good"}
    assert audit_entries[0].tenant_id == "tenant-1"
    assert audit_entries[0].org_id == "org-1"
    assert audit_entries[0].user_id == 1


def test_post_cad_review_rejects_invalid_state_without_commit() -> None:
    file_container = _file()
    client, db = _client(file_container=file_container)

    response = client.post(
        "/api/v1/cad/files/file-1/review",
        json={"state": "closed", "note": "no"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid review state: closed"
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_post_cad_review_returns_404_when_file_missing() -> None:
    client, _db = _client(file_container=None)

    response = client.post(
        "/api/v1/cad/files/file-1/review",
        json={"state": "approved", "note": "Looks good"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
