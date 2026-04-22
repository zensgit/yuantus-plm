from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_file_data_router import cad_file_data_router


class _FakeQuery:
    def __init__(self, jobs):
        self.jobs = jobs

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.jobs


class _FakeDb:
    def __init__(self, *, file_container=None, jobs=None):
        self.file_container = file_container
        self.jobs = jobs or []
        self.query = MagicMock(return_value=_FakeQuery(self.jobs))

    def get(self, model, identity):
        if model is FileContainer and self.file_container is not None:
            if getattr(self.file_container, "id", None) == identity:
                return self.file_container
        return None


def _client(file_container=None, jobs=None) -> tuple[TestClient, _FakeDb]:
    db = _FakeDb(file_container=file_container, jobs=jobs)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_file_data_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        roles=["engineer"],
        is_superuser=False,
        tenant_id="tenant-1",
        org_id="org-1",
    )
    return TestClient(app), db


def _file(**overrides):
    values = {
        "id": "file-1",
        "cad_format": "STEP",
        "cad_connector_id": "step",
        "cad_attributes": None,
        "cad_attributes_updated_at": None,
        "cad_attributes_source": None,
        "cad_bom_path": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _job(job_id: str, task_type: str, *, file_id: str = "file-1", result=None):
    return SimpleNamespace(
        id=job_id,
        task_type=task_type,
        status="completed",
        created_at=datetime(2026, 4, 22, 8, 0, 0),
        completed_at=datetime(2026, 4, 22, 8, 5, 0),
        payload={
            "file_id": file_id,
            "item_id": "item-1",
            "result": result or {},
        },
    )


def test_get_cad_attributes_returns_persisted_attributes_without_job_query() -> None:
    file_container = _file(
        cad_attributes={"mass": 12.3},
        cad_attributes_updated_at=datetime(2026, 4, 22, 9, 0, 0),
        cad_attributes_source="extractor",
    )
    client, db = _client(file_container=file_container)

    response = client.get("/api/v1/cad/files/file-1/attributes")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "cad_format": "STEP",
        "cad_connector_id": "step",
        "job_id": None,
        "job_status": "completed",
        "extracted_at": "2026-04-22T09:00:00",
        "extracted_attributes": {"mass": 12.3},
        "source": "extractor",
    }
    db.query.assert_not_called()


def test_get_cad_attributes_falls_back_to_matching_extract_job() -> None:
    file_container = _file()
    jobs = [
        _job("job-other", "cad_extract", file_id="file-other"),
        _job(
            "job-match",
            "cad_extract",
            result={"extracted_attributes": {"material": "AL"}, "source": "job"},
        ),
    ]
    client, _db = _client(file_container=file_container, jobs=jobs)

    response = client.get("/api/v1/cad/files/file-1/attributes")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-match"
    assert response.json()["job_status"] == "completed"
    assert response.json()["extracted_at"] == "2026-04-22T08:05:00"
    assert response.json()["extracted_attributes"] == {"material": "AL"}
    assert response.json()["source"] == "job"


def test_get_cad_attributes_returns_404_when_file_missing() -> None:
    client, _db = _client(file_container=None)

    response = client.get("/api/v1/cad/files/file-1/attributes")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_get_cad_bom_downloads_persisted_bom_json() -> None:
    file_container = _file(cad_bom_path="vault/cad/bom.json")
    client, _db = _client(file_container=file_container)

    def write_payload(_path, output_stream):
        output_stream.write(
            b'{"item_id":"item-1","imported_at":"2026-04-22T08:00:00",'
            b'"import_result":{"created":1},"bom":{"children":[{"id":"c1"}]}}'
        )

    with patch("yuantus.meta_engine.web.cad_file_data_router.FileService") as cls:
        cls.return_value.download_file.side_effect = write_payload

        response = client.get("/api/v1/cad/files/file-1/bom")

    assert response.status_code == 200
    assert response.json() == {
        "file_id": "file-1",
        "item_id": "item-1",
        "job_id": None,
        "job_status": "completed",
        "imported_at": "2026-04-22T08:00:00",
        "import_result": {"created": 1},
        "bom": {"children": [{"id": "c1"}]},
    }


def test_get_cad_bom_falls_back_to_matching_bom_job() -> None:
    file_container = _file()
    jobs = [
        _job("job-other", "cad_bom", file_id="file-other"),
        _job(
            "job-match",
            "cad_bom",
            result={"import_result": {"created": 2}, "bom": {"children": []}},
        ),
    ]
    client, _db = _client(file_container=file_container, jobs=jobs)

    response = client.get("/api/v1/cad/files/file-1/bom")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-match"
    assert response.json()["job_status"] == "completed"
    assert response.json()["imported_at"] == "2026-04-22T08:05:00"
    assert response.json()["import_result"] == {"created": 2}
    assert response.json()["bom"] == {"children": []}


def test_get_cad_bom_returns_404_when_no_persisted_payload_or_matching_job() -> None:
    client, _db = _client(file_container=_file(), jobs=[])

    response = client.get("/api/v1/cad/files/file-1/bom")

    assert response.status_code == 404
    assert response.json()["detail"] == "No cad_bom data found"
