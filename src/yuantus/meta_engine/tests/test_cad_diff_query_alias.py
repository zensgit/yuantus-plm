from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_diff_router import cad_diff_router


def _make_file(
    file_id: str,
    *,
    properties: dict[str, object] | None = None,
    schema_version: int | None = None,
) -> FileContainer:
    return FileContainer(
        id=file_id,
        cad_properties=properties,
        cad_document_schema_version=schema_version,
    )


def _client(file_map: dict[str, FileContainer]) -> TestClient:
    mock_db = MagicMock()
    mock_db.get.side_effect = lambda _model, file_id: file_map.get(file_id)

    app = FastAPI()
    app.include_router(cad_diff_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        roles=["admin"],
        tenant_id="tenant-1",
        org_id="org-1",
    )
    return TestClient(app)


def test_cad_diff_accepts_canonical_other_file_id() -> None:
    client = _client(
        {
            "file-a": _make_file(
                "file-a",
                properties={"name": "before", "stable": "same"},
                schema_version=1,
            ),
            "file-b": _make_file(
                "file-b",
                properties={"name": "after", "stable": "same", "new_key": "x"},
                schema_version=2,
            ),
        }
    )

    response = client.get(
        "/api/v1/cad/files/file-a/diff",
        params={"other_file_id": "file-b"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == "file-a"
    assert body["other_file_id"] == "file-b"
    assert body["properties"]["changed"] == {
        "name": {"from": "before", "to": "after"}
    }
    assert body["properties"]["added"] == {"new_key": "x"}
    assert body["properties"]["removed"] == {}
    assert body["cad_document_schema_version"] == {"from": 1, "to": 2}


def test_cad_diff_accepts_legacy_other_id_alias() -> None:
    client = _client(
        {
            "file-a": _make_file("file-a", properties={"status": "draft"}),
            "file-b": _make_file("file-b", properties={"status": "released"}),
        }
    )

    response = client.get(
        "/api/v1/cad/files/file-a/diff",
        params={"other_id": "file-b"},
    )

    assert response.status_code == 200
    assert response.json()["other_file_id"] == "file-b"


def test_cad_diff_prefers_canonical_param_when_both_are_present() -> None:
    client = _client(
        {
            "file-a": _make_file("file-a", properties={"revision": "A"}),
            "file-b": _make_file("file-b", properties={"revision": "B"}),
            "file-c": _make_file("file-c", properties={"revision": "C"}),
        }
    )

    response = client.get(
        "/api/v1/cad/files/file-a/diff",
        params={"other_file_id": "file-b", "other_id": "file-c"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["other_file_id"] == "file-b"
    assert body["properties"]["changed"] == {
        "revision": {"from": "A", "to": "B"}
    }


def test_cad_diff_requires_a_compare_target() -> None:
    client = _client({"file-a": _make_file("file-a", properties={"revision": "A"})})

    response = client.get("/api/v1/cad/files/file-a/diff")

    assert response.status_code == 422
    assert response.json()["detail"] == "other_file_id is required"


def test_cad_diff_returns_404_when_either_file_is_missing() -> None:
    client = _client({"file-a": _make_file("file-a", properties={"revision": "A"})})

    response = client.get(
        "/api/v1/cad/files/file-a/diff",
        params={"other_file_id": "missing-file"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
