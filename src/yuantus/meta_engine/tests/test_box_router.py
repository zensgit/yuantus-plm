"""Tests for box_router (C17 PLM Box Bootstrap)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.meta_engine.web.box_router import box_router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app():
    """Standalone FastAPI app with box_router mounted."""
    app = FastAPI()
    app.include_router(box_router, prefix="/api/v1")
    return app


def _client_with_mocks():
    """Return TestClient with mocked DB and user dependencies."""
    from yuantus.api.dependencies.auth import get_current_user
    from yuantus.database import get_db

    mock_db = MagicMock()
    user = SimpleNamespace(id=100, roles=["engineer"], is_superuser=False)

    app = _make_app()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), mock_db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_item():
    client, db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        fake_box = SimpleNamespace(
            id="box-1", name="Small Box", description=None, box_type="box",
            state="draft", width=100.0, height=80.0, depth=50.0,
            dimension_unit="mm", tare_weight=0.2, max_gross_weight=5.0,
            weight_unit="kg", material="cardboard", barcode="123",
            max_quantity=20, cost=1.0, product_id=None, is_active=True,
        )
        svc_cls.return_value.create_box.return_value = fake_box

        resp = client.post("/api/v1/box/items", json={"name": "Small Box"})

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["name"] == "Small Box"
    assert db.commit.called


def test_list_items():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        fake_box = SimpleNamespace(
            id="box-1", name="A", description=None, box_type="box",
            state="draft", width=None, height=None, depth=None,
            dimension_unit="mm", tare_weight=None, max_gross_weight=None,
            weight_unit="kg", material=None, barcode=None,
            max_quantity=None, cost=None, product_id=None, is_active=True,
        )
        svc_cls.return_value.list_boxes.return_value = [fake_box]

        resp = client.get("/api/v1/box/items")

    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_get_item():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        fake_box = SimpleNamespace(
            id="box-1", name="A", description=None, box_type="box",
            state="draft", width=None, height=None, depth=None,
            dimension_unit="mm", tare_weight=None, max_gross_weight=None,
            weight_unit="kg", material=None, barcode=None,
            max_quantity=None, cost=None, product_id=None, is_active=True,
        )
        svc_cls.return_value.get_box.return_value = fake_box

        resp = client.get("/api/v1/box/items/box-1")

    assert resp.status_code == 200
    assert resp.json()["id"] == "box-1"


def test_get_contents():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.get_box.return_value = SimpleNamespace(id="box-1")
        fake_content = SimpleNamespace(
            id="c-1", box_id="box-1", item_id="item-1",
            quantity=3.0, lot_serial=None, note=None,
        )
        svc_cls.return_value.list_contents.return_value = [fake_content]

        resp = client.get("/api/v1/box/items/box-1/contents")

    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["contents"][0]["item_id"] == "item-1"


def test_export_meta():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.export_meta.return_value = {
            "id": "box-1",
            "name": "Box",
            "box_type": "box",
            "state": "draft",
            "dimensions": {"width": 100, "height": 80, "depth": 50, "unit": "mm"},
            "weight": {"tare": 0.2, "max_gross": 5.0, "unit": "kg"},
            "material": "cardboard",
            "barcode": "123",
            "max_quantity": 20,
            "cost": 1.0,
            "product_id": None,
            "is_active": True,
            "contents": [],
        }

        resp = client.get("/api/v1/box/items/box-1/export-meta")

    assert resp.status_code == 200
    assert resp.json()["id"] == "box-1"
    assert "dimensions" in resp.json()
    assert "contents" in resp.json()


def test_not_found_404():
    client, _db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.get_box.return_value = None

        resp = client.get("/api/v1/box/items/nonexistent")

    assert resp.status_code == 404


def test_create_invalid_400():
    client, db = _client_with_mocks()

    with patch("yuantus.meta_engine.web.box_router.BoxService") as svc_cls:
        svc_cls.return_value.create_box.side_effect = ValueError("Invalid box_type")

        resp = client.post(
            "/api/v1/box/items",
            json={"name": "Bad", "box_type": "spaceship"},
        )

    assert resp.status_code == 400
    assert "Invalid box_type" in resp.json()["detail"]
    assert db.rollback.called
