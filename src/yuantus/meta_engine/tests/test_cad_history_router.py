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
from yuantus.meta_engine.web.cad_history_router import cad_history_router


class _FakeQuery:
    def __init__(self, logs):
        self.logs = logs
        self.seen_limit = None

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        self.seen_limit = value
        return self

    def all(self):
        if self.seen_limit is None:
            return self.logs
        return self.logs[: self.seen_limit]


class _FakeDb:
    def __init__(self, *, file_container=None, logs=None):
        self.file_container = file_container
        self.logs = logs or []
        self.query_obj = _FakeQuery(self.logs)
        self.query = MagicMock(return_value=self.query_obj)

    def get(self, model, identity):
        if model is FileContainer and self.file_container is not None:
            if getattr(self.file_container, "id", None) == identity:
                return self.file_container
        return None


def _client(file_container=None, logs=None) -> tuple[TestClient, _FakeDb]:
    db = _FakeDb(file_container=file_container, logs=logs)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_history_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=7,
        roles=["engineer"],
        is_superuser=False,
        tenant_id="tenant-1",
        org_id="org-1",
    )
    return TestClient(app), db


def _file(file_id: str = "file-1"):
    return SimpleNamespace(id=file_id)


def _log(log_id: str, action: str, *, payload=None, minute: int = 0, user_id=1):
    return SimpleNamespace(
        id=log_id,
        action=action,
        payload=payload,
        created_at=datetime(2026, 4, 22, 10, minute, 0),
        user_id=user_id,
    )


def test_get_cad_history_returns_ordered_entries_and_payload_fallback() -> None:
    logs = [
        _log(
            "cad-chg-2",
            "cad_review_update",
            payload={"state": "approved"},
            minute=5,
            user_id=1,
        ),
        _log("cad-chg-1", "cad_properties_update", payload=None, minute=0, user_id=None),
    ]
    client, db = _client(file_container=_file(), logs=logs)

    response = client.get("/api/v1/cad/files/file-1/history")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "entries": [
            {
                "id": "cad-chg-2",
                "action": "cad_review_update",
                "payload": {"state": "approved"},
                "created_at": "2026-04-22T10:05:00",
                "user_id": 1,
            },
            {
                "id": "cad-chg-1",
                "action": "cad_properties_update",
                "payload": {},
                "created_at": "2026-04-22T10:00:00",
                "user_id": None,
            },
        ],
    }
    db.query.assert_called_once_with(CadChangeLog)
    assert db.query_obj.seen_limit == 50


def test_get_cad_history_passes_limit_to_query() -> None:
    logs = [
        _log("cad-chg-3", "cad_review_update", minute=3),
        _log("cad-chg-2", "cad_review_update", minute=2),
        _log("cad-chg-1", "cad_review_update", minute=1),
    ]
    client, db = _client(file_container=_file(), logs=logs)

    response = client.get("/api/v1/cad/files/file-1/history", params={"limit": 2})

    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()["entries"]] == [
        "cad-chg-3",
        "cad-chg-2",
    ]
    assert db.query_obj.seen_limit == 2


def test_get_cad_history_returns_404_when_file_missing() -> None:
    client, db = _client(file_container=None, logs=[_log("cad-chg-1", "x")])

    response = client.get("/api/v1/cad/files/file-1/history")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
    db.query.assert_not_called()


def test_get_cad_history_rejects_invalid_limit_before_query() -> None:
    client, db = _client(file_container=_file(), logs=[])

    response = client.get("/api/v1/cad/files/file-1/history", params={"limit": 0})

    assert response.status_code == 422
    db.query.assert_not_called()
