from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.version.file_service import VersionFileError
from yuantus.meta_engine.version.models import ItemVersion


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client_with_state(
    *,
    item,
    current_version,
    file_container=None,
    existing_item_file=None,
    attachment=None,
    user_id: int = 7,
):
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    def override_get_user_id():
        return user_id

    def db_get(model, identity):
        if model is Item and item is not None and identity == item.id:
            return item
        if model is ItemVersion and current_version is not None and identity == current_version.id:
            return current_version
        if model is FileContainer and file_container is not None and identity == file_container.id:
            return file_container
        if model is ItemFile and attachment is not None and identity == attachment.id:
            return attachment
        if model is ItemType:
            return SimpleNamespace(id="part")
        return None

    def query_side_effect(model):
        query = MagicMock()
        if model is ItemFile:
            query.filter.return_value.first.return_value = existing_item_file
            return query
        return query

    mock_db.get.side_effect = db_get
    mock_db.query.side_effect = query_side_effect

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_get_user_id
    return TestClient(app), mock_db


def test_attach_existing_role_update_rejects_foreign_current_version_file_lock():
    item = SimpleNamespace(id="item-1", item_type_id="part", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    file_container = SimpleNamespace(id="file-1")
    existing = SimpleNamespace(
        id="att-1",
        item_id="item-1",
        file_id="file-1",
        file_role="attachment",
        description="old",
    )
    client, db = _client_with_state(
        item=item,
        current_version=version,
        file_container=file_container,
        existing_item_file=existing,
    )

    with patch("yuantus.meta_engine.web.file_router.is_item_locked", return_value=(False, None)), patch(
        "yuantus.meta_engine.web.file_router.VersionFileService"
    ) as vf_service_cls:
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        resp = client.post(
            "/api/v1/file/attach",
            json={
                "item_id": "item-1",
                "file_id": "file-1",
                "file_role": "geometry",
                "description": "new",
            },
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert not db.commit.called


def test_attach_new_item_file_rejects_foreign_current_version_file_lock():
    item = SimpleNamespace(id="item-1", item_type_id="part", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    file_container = SimpleNamespace(id="file-1")
    client, db = _client_with_state(
        item=item,
        current_version=version,
        file_container=file_container,
        existing_item_file=None,
    )

    with patch("yuantus.meta_engine.web.file_router.is_item_locked", return_value=(False, None)), patch(
        "yuantus.meta_engine.web.file_router.VersionFileService"
    ) as vf_service_cls:
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        resp = client.post(
            "/api/v1/file/attach",
            json={
                "item_id": "item-1",
                "file_id": "file-1",
                "file_role": "attachment",
            },
        )

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert not db.add.called


def test_attach_new_item_file_allows_missing_current_version_assoc():
    item = SimpleNamespace(id="item-1", item_type_id="part", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    file_container = SimpleNamespace(id="file-1")
    client, db = _client_with_state(
        item=item,
        current_version=version,
        file_container=file_container,
        existing_item_file=None,
    )

    with patch("yuantus.meta_engine.web.file_router.is_item_locked", return_value=(False, None)), patch(
        "yuantus.meta_engine.web.file_router.VersionFileService"
    ) as vf_service_cls:
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 with role attachment is not attached to version ver-1"
        )
        resp = client.post(
            "/api/v1/file/attach",
            json={
                "item_id": "item-1",
                "file_id": "file-1",
                "file_role": "attachment",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "created"
    assert db.add.called
    assert db.commit.called


def test_detach_attachment_rejects_foreign_current_version_file_lock():
    item = SimpleNamespace(id="item-1", item_type_id="part", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    attachment = SimpleNamespace(
        id="att-1",
        item_id="item-1",
        file_id="file-1",
        file_role="attachment",
    )
    client, db = _client_with_state(
        item=item,
        current_version=version,
        attachment=attachment,
    )

    with patch("yuantus.meta_engine.web.file_router.is_item_locked", return_value=(False, None)), patch(
        "yuantus.meta_engine.web.file_router.VersionFileService"
    ) as vf_service_cls:
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        resp = client.delete("/api/v1/file/attachment/att-1")

    assert resp.status_code == 409
    assert "checked out by another user" in resp.json()["detail"]
    assert not db.delete.called
