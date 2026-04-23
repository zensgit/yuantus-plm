from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from yuantus.meta_engine.models.file import FileContainer, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.cad_import_service import (
    CadImportConflictError,
    CadImportQuotaError,
    CadImportRequest,
    CadImportService,
    CadImportValidationError,
)
from yuantus.meta_engine.version.file_service import VersionFileError
from yuantus.meta_engine.version.models import ItemVersion


def _user(**overrides):
    data = {
        "id": 7,
        "username": "ada",
        "roles": ["engineer"],
        "is_superuser": False,
        "tenant_id": "tenant-1",
        "org_id": "org-1",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _request(**overrides):
    data = {
        "filename": "assy.step",
        "content": b"step-data",
        "item_id": None,
        "file_role": "native_cad",
        "author": None,
        "source_system": None,
        "source_version": None,
        "document_version": None,
        "cad_format": None,
        "cad_connector_id": None,
        "create_preview_job": False,
        "create_geometry_job": False,
        "geometry_format": "gltf",
        "create_extract_job": False,
        "create_bom_job": False,
        "auto_create_part": False,
        "create_dedup_job": False,
        "dedup_mode": "balanced",
        "dedup_index": False,
        "create_ml_job": False,
        "authorization": "Bearer token",
    }
    data.update(overrides)
    return CadImportRequest(**data)


def _file_container(**overrides):
    data = {
        "id": "file-1",
        "filename": "assy.step",
        "checksum": "abc123",
        "system_path": "3d/fi/file-1.step",
        "file_size": 123,
        "mime_type": "application/step",
        "file_type": "step",
        "document_type": "3d",
        "is_native_cad": True,
        "cad_format": "STEP",
        "cad_connector_id": "step",
        "author": None,
        "source_system": None,
        "source_version": None,
        "document_version": None,
        "preview_path": None,
        "geometry_path": None,
        "cad_manifest_path": None,
        "cad_document_path": None,
        "cad_metadata_path": None,
        "cad_bom_path": None,
        "cad_dedup_path": None,
        "cad_document_schema_version": None,
        "is_cad_file": lambda: True,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _chain_query(first_value=None, all_value=None):
    query = MagicMock()
    query.filter.return_value = query
    query.join.return_value = query
    query.order_by.return_value = query
    query.first.return_value = first_value
    query.all.return_value = [] if all_value is None else all_value
    return query


def _db(
    *,
    duplicate_file=None,
    item=None,
    existing_link=None,
    existing_part=None,
    current_version=None,
):
    db = MagicMock()
    file_query = _chain_query(duplicate_file)
    item_file_query = _chain_query(existing_link)
    item_query = _chain_query(existing_part)
    version_query = _chain_query(all_value=[])

    def query_side_effect(model, *args):
        if model is FileContainer:
            return file_query
        if model is ItemFile:
            return item_file_query
        if model is Item:
            return item_query
        return version_query

    def get_side_effect(model, identity):
        if model is Item and item is not None and identity == item.id:
            return item
        if model is ItemVersion and current_version is not None and identity == current_version.id:
            return current_version
        if identity == "Part":
            return None
        return None

    db.query.side_effect = query_side_effect
    db.get.side_effect = get_side_effect
    return db


def _part_type():
    return SimpleNamespace(
        id="Part",
        properties=[
            SimpleNamespace(name="item_number", is_cad_synced=False, length=None, ui_options=None),
            SimpleNamespace(name="description", is_cad_synced=False, length=None, ui_options=None),
            SimpleNamespace(name="name", is_cad_synced=False, length=None, ui_options=None),
            SimpleNamespace(name="revision", is_cad_synced=False, length=None, ui_options=None),
        ],
    )


def test_new_file_hard_quota_raises_quota_error():
    db = _db(duplicate_file=None)
    identity_db = MagicMock()

    with patch("yuantus.meta_engine.services.cad_import_service.QuotaService") as quota_cls:
        quota_cls.return_value.evaluate.return_value = ["over"]
        quota_cls.return_value.mode = "hard"
        quota_cls.build_error_payload.return_value = {"violations": ["files"]}

        with pytest.raises(CadImportQuotaError) as exc_info:
            CadImportService(db, identity_db).import_file(_request(), _user())

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "QUOTA_EXCEEDED"
    assert exc_info.value.detail["violations"] == ["files"]


def test_duplicate_missing_storage_repairs_after_lock_guard():
    duplicate = _file_container(system_path="3d/fi/file-1.step")
    db = _db(duplicate_file=duplicate)
    identity_db = MagicMock()

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service._ensure_duplicate_file_repair_editable"
    ) as repair_guard:
        file_service_cls.return_value.file_exists.return_value = False

        result = CadImportService(db, identity_db).import_file(_request(), _user())

    repair_guard.assert_called_once_with(db, duplicate, user_id=7)
    file_service_cls.return_value.upload_file.assert_called_once()
    assert duplicate.file_size == len(b"step-data")
    assert duplicate.mime_type == "application/octet-stream"
    assert result.file_container is duplicate
    assert result.is_duplicate is True


def test_create_bom_job_without_item_or_auto_part_raises_validation_error():
    duplicate = _file_container()
    db = _db(duplicate_file=duplicate)

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls:
        file_service_cls.return_value.file_exists.return_value = True
        with pytest.raises(CadImportValidationError) as exc_info:
            CadImportService(db, MagicMock()).import_file(
                _request(create_bom_job=True),
                _user(),
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "create_bom_job requires item_id or auto_create_part"


def test_auto_part_updates_existing_part_missing_fields():
    duplicate = _file_container()
    existing_part = SimpleNamespace(
        id="part-1",
        properties={"item_number": "P-100", "description": ""},
        current_version_id=None,
    )
    db = _db(duplicate_file=duplicate, existing_part=existing_part)

    def get_side_effect(model, identity):
        if identity == "Part":
            return _part_type()
        if model is Item and identity == "part-1":
            return existing_part
        return None

    db.get.side_effect = get_side_effect

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.CadService"
    ) as cad_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.AMLEngine"
    ) as engine_cls:
        file_service_cls.return_value.file_exists.return_value = True
        cad_service_cls.return_value.extract_attributes_for_file.return_value = (
            {"item_number": "P-100", "description": "Bracket"},
            "cad",
        )

        result = CadImportService(db, MagicMock()).import_file(
            _request(auto_create_part=True),
            _user(),
        )

    assert result.item_id == "part-1"
    applied = engine_cls.return_value.apply.call_args.args[0]
    assert applied.action.value == "update"
    assert applied.properties == {"description": "Bracket", "name": "Bracket"}
    assert db.commit.called


def test_auto_part_creates_new_part_when_no_existing_part():
    duplicate = _file_container()
    db = _db(duplicate_file=duplicate, existing_part=None)

    def get_side_effect(model, identity):
        if identity == "Part":
            return _part_type()
        if model is Item and identity == "part-new":
            return SimpleNamespace(id="part-new", current_version_id=None)
        return None

    db.get.side_effect = get_side_effect

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.CadService"
    ) as cad_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.AMLEngine"
    ) as engine_cls:
        file_service_cls.return_value.file_exists.return_value = True
        cad_service_cls.return_value.extract_attributes_for_file.return_value = (
            {"item_number": "P-200", "description": "Housing"},
            "cad",
        )
        engine_cls.return_value.apply.return_value = {"id": "part-new"}

        result = CadImportService(db, MagicMock()).import_file(
            _request(auto_create_part=True),
            _user(is_superuser=True),
        )

    assert result.item_id == "part-new"
    add_item = engine_cls.return_value.apply.call_args.args[0]
    assert add_item.action.value == "add"
    assert add_item.properties["item_number"] == "P-200"
    assert "superuser" in engine_cls.call_args.kwargs["roles"]


def test_existing_item_file_link_role_update_checks_old_and_new_roles():
    duplicate = _file_container()
    item = SimpleNamespace(id="item-1", current_version_id="ver-1")
    existing_link = SimpleNamespace(
        id="att-1",
        item_id="item-1",
        file_id="file-1",
        file_role="native_cad",
    )
    db = _db(duplicate_file=duplicate, item=item, existing_link=existing_link)

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service._ensure_current_version_attachment_editable"
    ) as guard:
        file_service_cls.return_value.file_exists.return_value = True
        result = CadImportService(db, MagicMock()).import_file(
            _request(item_id="item-1", file_role="geometry"),
            _user(),
        )

    assert result.attachment_id == "att-1"
    assert existing_link.file_role == "geometry"
    assert [call.kwargs["file_role"] for call in guard.call_args_list] == [
        "native_cad",
        "geometry",
    ]


def test_new_item_file_link_checks_editability_before_insert():
    duplicate = _file_container()
    item = SimpleNamespace(id="item-1", current_version_id="ver-1")
    db = _db(duplicate_file=duplicate, item=item, existing_link=None)

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service._ensure_current_version_attachment_editable"
    ) as guard:
        file_service_cls.return_value.file_exists.return_value = True
        result = CadImportService(db, MagicMock()).import_file(
            _request(item_id="item-1"),
            _user(),
        )

    guard.assert_called_once()
    added = db.add.call_args.args[0]
    assert isinstance(added, ItemFile)
    assert added.item_id == "item-1"
    assert added.file_id == "file-1"
    assert result.attachment_id == added.id


def test_job_planning_enforces_active_job_quota_before_enqueue():
    duplicate = _file_container()
    db = _db(duplicate_file=duplicate)

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.QuotaService"
    ) as quota_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.JobService"
    ) as job_service_cls:
        file_service_cls.return_value.file_exists.return_value = True
        quota_cls.return_value.evaluate.return_value = ["active_jobs"]
        quota_cls.return_value.mode = "hard"
        quota_cls.build_error_payload.return_value = {"violations": ["active_jobs"]}

        with pytest.raises(CadImportQuotaError):
            CadImportService(db, MagicMock()).import_file(
                _request(
                    create_preview_job=True,
                    create_geometry_job=True,
                    create_extract_job=None,
                ),
                _user(),
            )

    quota_cls.return_value.evaluate.assert_called_once_with(
        "tenant-1",
        deltas={"active_jobs": 3},
    )
    job_service_cls.return_value.create_job.assert_not_called()


def test_enqueued_payload_includes_scope_auth_cad_metadata_and_item_id():
    duplicate = _file_container()
    item = SimpleNamespace(id="item-1", current_version_id=None)
    db = _db(duplicate_file=duplicate, item=item)
    job = SimpleNamespace(id="job-1", task_type="cad_preview", status="pending")

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.QuotaService"
    ) as quota_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.JobService"
    ) as job_service_cls:
        file_service_cls.return_value.file_exists.return_value = True
        quota_cls.return_value.evaluate.return_value = []
        job_service_cls.return_value.create_job.return_value = job

        result = CadImportService(db, MagicMock()).import_file(
            _request(item_id="item-1", create_preview_job=True),
            _user(),
        )

    payload = job_service_cls.return_value.create_job.call_args.kwargs["payload"]
    assert payload["item_id"] == "item-1"
    assert payload["file_id"] == "file-1"
    assert payload["source_path"] == "3d/fi/file-1.step"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["org_id"] == "org-1"
    assert payload["user_id"] == 7
    assert payload["roles"] == ["engineer"]
    assert payload["authorization"] == "Bearer token"
    assert payload["cad_connector_id"] == "step"
    assert payload["cad_format"] == "STEP"
    assert payload["document_type"] == "3d"
    assert result.jobs[0].id == "job-1"


def test_dedup_job_payload_preserves_mode_user_name_and_index():
    duplicate = _file_container(
        file_type="dwg",
        document_type="2d",
        cad_format="AUTOCAD",
        cad_connector_id="autocad",
    )
    db = _db(duplicate_file=duplicate)
    job = SimpleNamespace(id="job-1", task_type="cad_dedup_vision", status="pending")

    with patch("yuantus.meta_engine.services.cad_import_service.FileService") as file_service_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.QuotaService"
    ) as quota_cls, patch(
        "yuantus.meta_engine.services.cad_import_service.JobService"
    ) as job_service_cls:
        file_service_cls.return_value.file_exists.return_value = True
        quota_cls.return_value.evaluate.return_value = []
        job_service_cls.return_value.create_job.return_value = job

        CadImportService(db, MagicMock()).import_file(
            _request(
                filename="drawing.dwg",
                create_dedup_job=True,
                dedup_mode="precise",
                dedup_index=True,
            ),
            _user(username="grace"),
        )

    payload = job_service_cls.return_value.create_job.call_args.kwargs["payload"]
    assert payload["mode"] == "precise"
    assert payload["user_name"] == "grace"
    assert payload["index"] is True


def test_file_lock_conflict_maps_to_service_conflict_error():
    item = SimpleNamespace(id="item-1", current_version_id="ver-1")
    version = SimpleNamespace(id="ver-1", checked_out_by_id=None)
    db = _db(item=item, current_version=version)

    with patch("yuantus.meta_engine.services.cad_import_service.VersionFileService") as vf_service_cls:
        vf_service_cls.return_value.ensure_file_editable.side_effect = VersionFileError(
            "File file-1 is checked out by another user"
        )
        with pytest.raises(CadImportConflictError) as exc_info:
            from yuantus.meta_engine.services.cad_import_service import (
                _ensure_current_version_attachment_editable,
            )

            _ensure_current_version_attachment_editable(
                db,
                item,
                file_id="file-1",
                file_role="native_cad",
                user_id=7,
            )

    assert exc_info.value.status_code == 409
    assert "checked out by another user" in exc_info.value.detail
