from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.file_service import VersionFileError
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.security.auth.database import get_identity_db


def _mock_file_container(file_id: str = "file-1"):
    return SimpleNamespace(
        id=file_id,
        filename="assy.step",
        checksum="abc123",
        system_path=f"cad/{file_id}.step",
        file_size=123,
        mime_type="application/step",
        file_type="step",
        document_type="cad",
        is_native_cad=True,
        cad_format="step",
        cad_connector_id=None,
        author=None,
        source_system=None,
        source_version=None,
        document_version=None,
        preview_path=None,
        geometry_path=None,
        cad_manifest_path=None,
        cad_document_path=None,
        cad_metadata_path=None,
        cad_bom_path=None,
        cad_dedup_path=None,
        cad_document_schema_version=None,
        is_cad_file=lambda: True,
    )


def _client_with_state(
    *,
    item,
    current_version,
    duplicate_file,
    existing_item_file=None,
    user_id: int = 7,
):
    mock_db = MagicMock()
    identity_db = MagicMock()
    user = SimpleNamespace(
        id=user_id,
        roles=["engineer"],
        is_superuser=False,
        tenant_id="tenant-1",
        org_id="org-1",
    )

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def override_get_identity_db():
        try:
            yield identity_db
        finally:
            pass

    def db_get(model, identity):
        if model is Item and item is not None and identity == item.id:
            return item
        if model is ItemVersion and current_version is not None and identity == current_version.id:
            return current_version
        return None

    def query_side_effect(model):
        query = MagicMock()
        if model is FileContainer:
            query.filter.return_value.first.return_value = duplicate_file
            return query
        if model is ItemFile:
            query.filter.return_value.first.return_value = existing_item_file
            return query
        return query

    mock_db.get.side_effect = db_get
    mock_db.query.side_effect = query_side_effect

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_identity_db] = override_get_identity_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), mock_db


def _import_payload(**overrides):
    payload = {
        "item_id": "item-1",
        "file_role": "native_cad",
        "create_preview_job": "false",
        "create_geometry_job": "false",
        "create_extract_job": "false",
        "create_bom_job": "false",
        "create_dedup_job": "false",
        "create_ml_job": "false",
    }
    payload.update(overrides)
    return payload


def test_cad_import_existing_link_role_update_rejects_foreign_file_lock():
    item = SimpleNamespace(id="item-1", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    duplicate_file = _mock_file_container()
    existing_link = SimpleNamespace(
        id="att-1",
        item_id="item-1",
        file_id="file-1",
        file_role="attachment",
    )
    client, db = _client_with_state(
        item=item,
        current_version=version,
        duplicate_file=duplicate_file,
        existing_item_file=existing_link,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.web.cad_router.VersionFileService"
    ) as vf_service_cls:
        file_service_cls.return_value.file_exists.return_value = True
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        resp = client.post(
            "/api/v1/cad/import",
            data=_import_payload(file_role="geometry"),
            files={"file": ("assy.step", b"step-data", "application/octet-stream")},
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert not db.commit.called


def test_cad_import_new_link_rejects_foreign_file_lock():
    item = SimpleNamespace(id="item-1", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    duplicate_file = _mock_file_container()
    client, db = _client_with_state(
        item=item,
        current_version=version,
        duplicate_file=duplicate_file,
        existing_item_file=None,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.web.cad_router.VersionFileService"
    ) as vf_service_cls:
        file_service_cls.return_value.file_exists.return_value = True
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        resp = client.post(
            "/api/v1/cad/import",
            data=_import_payload(),
            files={"file": ("assy.step", b"step-data", "application/octet-stream")},
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert not db.add.called


def test_cad_import_new_link_allows_missing_current_version_assoc():
    item = SimpleNamespace(id="item-1", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    duplicate_file = _mock_file_container()
    client, db = _client_with_state(
        item=item,
        current_version=version,
        duplicate_file=duplicate_file,
        existing_item_file=None,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.web.cad_router.VersionFileService"
    ) as vf_service_cls:
        file_service_cls.return_value.file_exists.return_value = True
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 with role native_cad is not attached to version ver-1"
        )
        resp = client.post(
            "/api/v1/cad/import",
            data=_import_payload(),
            files={"file": ("assy.step", b"step-data", "application/octet-stream")},
        )

    assert resp.status_code == 200
    assert db.add.called
    assert db.commit.called
    vf_service_cls.return_value.ensure_file_editable.assert_called_once_with(
        "ver-1",
        "file-1",
        7,
        file_role="native_cad",
    )


def test_cad_import_duplicate_repair_rejects_foreign_current_version_lock():
    duplicate_file = _mock_file_container()
    client, db = _client_with_state(
        item=None,
        current_version=None,
        duplicate_file=duplicate_file,
        existing_item_file=None,
    )

    with patch("yuantus.meta_engine.web.cad_router.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.web.cad_router._ensure_duplicate_file_repair_editable"
    ) as repair_guard:
        file_service_cls.return_value.file_exists.return_value = False
        repair_guard.side_effect = HTTPException(
            status_code=409,
            detail="File file-1 is checked out by another user",
        )
        resp = client.post(
            "/api/v1/cad/import",
            data={
                "create_preview_job": "false",
                "create_geometry_job": "false",
                "create_extract_job": "false",
                "create_bom_job": "false",
                "create_dedup_job": "false",
                "create_ml_job": "false",
            },
            files={"file": ("assy.step", b"step-data", "application/octet-stream")},
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    file_service_cls.return_value.upload_file.assert_not_called()
    assert not db.commit.called
