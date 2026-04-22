from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import require_admin_user
from yuantus.database import get_db
from yuantus.meta_engine.web.cad_sync_template_router import (
    _csv_bool,
    cad_sync_template_router,
)


class _FakeQuery:
    def __init__(self, item_type):
        self.item_type = item_type

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.item_type


class _FakeDb:
    def __init__(self, item_type):
        self.item_type = item_type
        self.add = MagicMock()
        self.commit = MagicMock()

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self.item_type)


def _client(item_type) -> tuple[TestClient, _FakeDb]:
    db = _FakeDb(item_type)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app = FastAPI()
    app.include_router(cad_sync_template_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin_user] = lambda: SimpleNamespace(
        id=1,
        roles=["admin"],
        is_superuser=True,
        tenant_id="tenant-1",
        org_id="org-1",
    )
    return TestClient(app), db


def _prop(
    name: str,
    *,
    label: str | None = None,
    data_type: str = "string",
    is_cad_synced: bool = False,
    ui_options=None,
):
    return SimpleNamespace(
        name=name,
        label=label or name.title(),
        data_type=data_type,
        is_cad_synced=is_cad_synced,
        ui_options=ui_options or {},
    )


def _item_type(*props):
    return SimpleNamespace(
        id="Part",
        properties=list(props),
        properties_schema={"cached": True},
    )


def test_get_cad_sync_template_json_resolves_cad_keys_for_synced_properties() -> None:
    item_type = _item_type(
        _prop("item_number", label="Item Number", is_cad_synced=True, ui_options={"cad_key": "part_number"}),
        _prop("description", label="Description", is_cad_synced=False),
    )
    client, _db = _client(item_type)

    response = client.get("/api/v1/cad/sync-template/Part?output_format=json")

    assert response.status_code == 200
    assert response.json() == {
        "item_type_id": "Part",
        "properties": [
            {
                "property_name": "item_number",
                "label": "Item Number",
                "data_type": "string",
                "is_cad_synced": True,
                "cad_key": "part_number",
            },
            {
                "property_name": "description",
                "label": "Description",
                "data_type": "string",
                "is_cad_synced": False,
                "cad_key": None,
            },
        ],
    }


def test_get_cad_sync_template_csv_returns_attachment() -> None:
    item_type = _item_type(
        _prop("item_number", label="Item Number", is_cad_synced=True, ui_options='{"cad_key":"part_number"}'),
        _prop("description", label="Description", is_cad_synced=False),
    )
    client, _db = _client(item_type)

    response = client.get("/api/v1/cad/sync-template/Part")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        'attachment; filename="cad_sync_template_Part.csv"'
    )
    assert response.text.splitlines() == [
        "property_name,label,data_type,is_cad_synced,cad_key",
        "item_number,Item Number,string,true,part_number",
        "description,Description,string,false,",
    ]


def test_get_cad_sync_template_missing_item_type_returns_404() -> None:
    client, _db = _client(None)

    response = client.get("/api/v1/cad/sync-template/Part?output_format=json")

    assert response.status_code == 404
    assert response.json()["detail"] == "ItemType not found"


def test_apply_cad_sync_template_updates_properties_and_invalidates_schema() -> None:
    prop = _prop("item_number", label="Item Number", is_cad_synced=False)
    item_type = _item_type(prop)
    client, db = _client(item_type)
    csv_payload = (
        "property_name,is_cad_synced,cad_key\n"
        "item_number,true,part_number\n"
        "unknown,true,missing_key\n"
        ",true,ignored\n"
    )

    response = client.post(
        "/api/v1/cad/sync-template/Part",
        files={"file": ("template.csv", csv_payload, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "item_type_id": "Part",
        "updated": 1,
        "skipped": 1,
        "missing": ["unknown"],
    }
    assert prop.is_cad_synced is True
    assert prop.ui_options == {"cad_key": "part_number"}
    assert item_type.properties_schema is None
    assert db.add.call_args_list[0].args == (prop,)
    assert db.add.call_args_list[1].args == (item_type,)
    db.commit.assert_called_once_with()


def test_apply_cad_sync_template_accepts_name_and_cad_attribute_aliases() -> None:
    prop = _prop("revision", is_cad_synced=False)
    item_type = _item_type(prop)
    client, _db = _client(item_type)
    csv_payload = "name,is_cad_synced,cad_attribute\nrevision,yes,REV\n"

    response = client.post(
        "/api/v1/cad/sync-template/Part",
        files={"file": ("template.csv", csv_payload, "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 1
    assert prop.is_cad_synced is True
    assert prop.ui_options == {"cad_key": "REV"}


def test_apply_cad_sync_template_empty_file_returns_400() -> None:
    client, _db = _client(_item_type())

    response = client.post(
        "/api/v1/cad/sync-template/Part",
        files={"file": ("template.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty template file"


def test_csv_bool_keeps_existing_permissive_values() -> None:
    assert _csv_bool("1") is True
    assert _csv_bool("yes") is True
    assert _csv_bool("0") is False
    assert _csv_bool("n") is False
    assert _csv_bool("maybe") is None
    assert _csv_bool(None) is None
