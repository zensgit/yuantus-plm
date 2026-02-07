from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import zipfile

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item


def _client_with_user(user):
    mock_db_session = MagicMock()

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


def _mock_impact_service(service):
    service.where_used_summary.return_value = {
        "total": 0,
        "hits": [],
        "recursive": False,
        "max_levels": 10,
    }
    service.baselines_summary.return_value = {"total": 0, "hits": []}
    service.esign_summary.return_value = {
        "total": 0,
        "valid": 0,
        "revoked": 0,
        "expired": 0,
        "latest_signed_at": None,
        "latest_signatures": [],
        "latest_manifest": None,
    }


def _mock_readiness_payload(*, item_id: str, ruleset_id: str):
    return {
        "item_id": item_id,
        "generated_at": "2026-02-07T00:00:00Z",
        "ruleset_id": ruleset_id,
        "summary": {
            "ok": True,
            "resources": 0,
            "ok_resources": 0,
            "error_count": 0,
            "warning_count": 0,
            "by_kind": {},
        },
        "resources": [],
        "esign_manifest": None,
    }


def test_cockpit_denies_non_admin():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    resp = client.get("/api/v1/items/item-1/cockpit")
    assert resp.status_code == 403


def test_cockpit_404_when_item_missing():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)
    db.get.return_value = None

    resp = client.get("/api/v1/items/item-404/cockpit")
    assert resp.status_code == 404


def test_cockpit_happy_path_includes_impact_readiness_ecos_and_links():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    db.get.return_value = Item(
        id="item-1",
        item_type_id="Part",
        config_id="P-1",
        generation=1,
        state="released",
        properties={"item_number": "P-1", "name": "Part 1", "revision": "A"},
    )

    with (
        patch("yuantus.meta_engine.web.item_cockpit_router.ImpactAnalysisService") as impact_cls,
        patch(
            "yuantus.meta_engine.web.item_cockpit_router.ReleaseReadinessService"
        ) as readiness_cls,
        patch("yuantus.meta_engine.web.item_cockpit_router.ECOService") as eco_cls,
    ):
        impact = impact_cls.return_value
        _mock_impact_service(impact)

        readiness = readiness_cls.return_value
        readiness.get_item_release_readiness.return_value = _mock_readiness_payload(
            item_id="item-1",
            ruleset_id="readiness",
        )

        eco = eco_cls.return_value
        eco.list_ecos.return_value = []

        resp = client.get("/api/v1/items/item-1/cockpit?ruleset_id=readiness")

    assert resp.status_code == 200
    data = resp.json()
    assert data["item"]["id"] == "item-1"
    assert "generated_at" in data
    assert data["impact_summary"]["item_id"] == "item-1"
    assert data["release_readiness"]["ruleset_id"] == "readiness"
    assert data["open_ecos"]["total"] == 0
    assert "impact_export" in data["links"]
    assert "release_readiness_export" in data["links"]


def test_cockpit_export_json_sets_filename_and_type():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    db.get.return_value = Item(
        id="item-1",
        item_type_id="Part",
        config_id="P-1",
        generation=1,
        state="released",
        properties={"item_number": "P-1", "name": "Part 1", "revision": "A"},
    )

    with (
        patch("yuantus.meta_engine.web.item_cockpit_router.ImpactAnalysisService") as impact_cls,
        patch(
            "yuantus.meta_engine.web.item_cockpit_router.ReleaseReadinessService"
        ) as readiness_cls,
        patch("yuantus.meta_engine.web.item_cockpit_router.ECOService") as eco_cls,
    ):
        impact = impact_cls.return_value
        _mock_impact_service(impact)

        readiness = readiness_cls.return_value
        readiness.get_item_release_readiness.return_value = _mock_readiness_payload(
            item_id="item-1",
            ruleset_id="readiness",
        )

        eco = eco_cls.return_value
        eco.list_ecos.return_value = []

        resp = client.get("/api/v1/items/item-1/cockpit/export?export_format=json")

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/json")
    cd = resp.headers.get("content-disposition", "")
    assert 'filename="item-cockpit-item-1.json"' in cd


def test_cockpit_export_zip_contains_expected_files():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    db.get.return_value = Item(
        id="item-1",
        item_type_id="Part",
        config_id="P-1",
        generation=1,
        state="released",
        properties={"item_number": "P-1", "name": "Part 1", "revision": "A"},
    )

    with (
        patch("yuantus.meta_engine.web.item_cockpit_router.ImpactAnalysisService") as impact_cls,
        patch(
            "yuantus.meta_engine.web.item_cockpit_router.ReleaseReadinessService"
        ) as readiness_cls,
        patch("yuantus.meta_engine.web.item_cockpit_router.ECOService") as eco_cls,
    ):
        impact = impact_cls.return_value
        _mock_impact_service(impact)

        readiness = readiness_cls.return_value
        readiness.get_item_release_readiness.return_value = _mock_readiness_payload(
            item_id="item-1",
            ruleset_id="readiness",
        )

        eco = eco_cls.return_value
        eco.list_ecos.return_value = []

        resp = client.get("/api/v1/items/item-1/cockpit/export?export_format=zip")

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/zip")

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = set(zf.namelist())
    assert "cockpit.json" in names
    assert "where_used.csv" in names
    assert "baselines.csv" in names
    assert "signatures.csv" in names
    assert "readiness_resources.csv" in names
    assert "readiness_errors.csv" in names
    assert "readiness_warnings.csv" in names
    assert "open_ecos.csv" in names

