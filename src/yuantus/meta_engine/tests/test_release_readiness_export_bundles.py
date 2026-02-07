import io
import json
import zipfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item


def _client_with_user(user, *, item_exists: bool):
    mock_db_session = MagicMock()
    mock_db_session.get.return_value = (
        Item(id="item-1", item_type_id="Part", properties={}, state="draft")
        if item_exists
        else None
    )

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), mock_db_session


def test_release_readiness_export_denies_non_admin():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user, item_exists=True)

    resp = client.get("/api/v1/release-readiness/items/item-1/export")
    assert resp.status_code == 403


def test_release_readiness_export_returns_404_when_item_missing():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user, item_exists=False)

    resp = client.get("/api/v1/release-readiness/items/item-404/export")
    assert resp.status_code == 404


def test_release_readiness_export_zip_happy_path():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user, item_exists=True)

    payload = {
        "item_id": "item-1",
        "ruleset_id": "readiness",
        "generated_at": "2026-02-07T00:00:00Z",
        "summary": {
            "ok": False,
            "resources": 1,
            "ok_resources": 0,
            "error_count": 1,
            "warning_count": 1,
            "by_kind": {
                "mbom_release": {
                    "resources": 1,
                    "ok_resources": 0,
                    "error_count": 1,
                    "warning_count": 1,
                }
            },
        },
        "resources": [
            {
                "kind": "mbom_release",
                "resource_type": "mbom",
                "resource_id": "mbom-1",
                "name": "MBOM 1",
                "state": "draft",
                "ruleset_id": "readiness",
                "errors": [
                    {
                        "code": "mbom_empty_structure",
                        "message": "MBOM structure is empty: mbom-1",
                        "rule_id": "mbom.has_non_empty_structure",
                        "details": {"mbom_id": "mbom-1"},
                    }
                ],
                "warnings": [
                    {
                        "code": "mbom_warning",
                        "message": "MBOM warning",
                        "rule_id": "mbom.warning",
                        "details": {"mbom_id": "mbom-1"},
                    }
                ],
            }
        ],
        "esign_manifest": {"manifest_id": "m1", "is_complete": False},
    }

    with patch("yuantus.meta_engine.web.release_readiness_router.ReleaseReadinessService") as cls:
        svc = cls.return_value
        svc.get_item_release_readiness.return_value = payload

        resp = client.get(
            "/api/v1/release-readiness/items/item-1/export?export_format=zip"
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-disposition", "").endswith("release-readiness-item-1.zip\"")

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = set(zf.namelist())
    assert "readiness.json" in names
    assert "resources.csv" in names
    assert "errors.csv" in names
    assert "warnings.csv" in names
    assert "esign_manifest.json" in names

    readiness = json.loads(zf.read("readiness.json"))
    assert readiness["item_id"] == "item-1"

    csv_text = zf.read("errors.csv").decode("utf-8-sig")
    assert csv_text.splitlines()[0].startswith("kind,")


def test_release_readiness_export_json_happy_path():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, _db = _client_with_user(user, item_exists=True)

    payload = {
        "item_id": "item-1",
        "ruleset_id": "readiness",
        "summary": {"ok": True, "resources": 0, "ok_resources": 0, "error_count": 0, "warning_count": 0, "by_kind": {}},
        "resources": [],
        "esign_manifest": None,
    }

    with patch("yuantus.meta_engine.web.release_readiness_router.ReleaseReadinessService") as cls:
        svc = cls.return_value
        svc.get_item_release_readiness.return_value = payload

        resp = client.get(
            "/api/v1/release-readiness/items/item-1/export?export_format=json"
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-disposition", "").endswith("release-readiness-item-1.json\"")
    data = resp.json()
    assert data["item_id"] == "item-1"

