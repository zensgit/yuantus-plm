from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_mesh_stats_router import cad_mesh_stats_router


class _FakeDb:
    def __init__(self, *, file_container=None):
        self.file_container = file_container

    def get(self, model, identity):
        if model is FileContainer and self.file_container is not None:
            if getattr(self.file_container, "id", None) == identity:
                return self.file_container
        return None


def _client(file_container=None) -> TestClient:
    db = _FakeDb(file_container=file_container)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_mesh_stats_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        roles=["engineer"],
        is_superuser=False,
        tenant_id="tenant-1",
        org_id="org-1",
    )
    return TestClient(app)


def _file(**overrides):
    values = {
        "id": "file-1",
        "cad_metadata_path": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_get_cad_mesh_stats_returns_404_when_file_missing() -> None:
    client = _client(file_container=None)

    response = client.get("/api/v1/cad/files/file-1/mesh-stats")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_get_cad_mesh_stats_reports_missing_metadata_path() -> None:
    client = _client(file_container=_file())

    response = client.get("/api/v1/cad/files/file-1/mesh-stats")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "stats": {
            "available": False,
            "reason": "CAD metadata not available",
        },
    }


def test_get_cad_mesh_stats_reports_attribute_payload_as_unavailable() -> None:
    client = _client(file_container=_file(cad_metadata_path="vault/cad/metadata.json"))

    def write_payload(_path, output_stream):
        output_stream.write(b'{"kind":"cad_attributes","mass":12.3}')

    with patch("yuantus.meta_engine.web.cad_mesh_stats_router.FileService") as cls:
        cls.return_value.download_file.side_effect = write_payload

        response = client.get("/api/v1/cad/files/file-1/mesh-stats")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "stats": {
            "available": False,
            "reason": "CAD mesh metadata not available",
        },
    }


def test_get_cad_mesh_stats_reports_raw_keys_when_payload_is_not_mesh() -> None:
    client = _client(file_container=_file(cad_metadata_path="vault/cad/metadata.json"))

    def write_payload(_path, output_stream):
        output_stream.write(b'{"kind":"other","source":"fixture"}')

    with patch("yuantus.meta_engine.web.cad_mesh_stats_router.FileService") as cls:
        cls.return_value.download_file.side_effect = write_payload

        response = client.get("/api/v1/cad/files/file-1/mesh-stats")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "stats": {
            "available": False,
            "reason": "CAD mesh metadata not available",
            "raw_keys": ["kind", "source"],
        },
    }


def test_get_cad_mesh_stats_extracts_mesh_metadata() -> None:
    client = _client(file_container=_file(cad_metadata_path="vault/cad/metadata.json"))

    def write_payload(_path, output_stream):
        output_stream.write(
            b'{"kind":"mesh_metadata","entities":[{"id":1},{"id":2}],'
            b'"triangles":[1,2,3],"bounds":{"min":{"x":0},"max":{"x":1}}}'
        )

    with patch("yuantus.meta_engine.web.cad_mesh_stats_router.FileService") as cls:
        cls.return_value.download_file.side_effect = write_payload

        response = client.get("/api/v1/cad/files/file-1/mesh-stats")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "stats": {
            "raw_keys": ["bounds", "entities", "kind", "triangles"],
            "entity_count": 2,
            "triangle_count": 3,
            "bounds": {"min": {"x": 0}, "max": {"x": 1}},
            "available": True,
        },
    }


def test_get_cad_mesh_stats_returns_500_for_invalid_metadata_json() -> None:
    client = _client(file_container=_file(cad_metadata_path="vault/cad/metadata.json"))

    def write_payload(_path, output_stream):
        output_stream.write(b"{")

    with patch("yuantus.meta_engine.web.cad_mesh_stats_router.FileService") as cls:
        cls.return_value.download_file.side_effect = write_payload

        response = client.get("/api/v1/cad/files/file-1/mesh-stats")

    assert response.status_code == 500
    assert response.json()["detail"] == "CAD metadata invalid JSON"
