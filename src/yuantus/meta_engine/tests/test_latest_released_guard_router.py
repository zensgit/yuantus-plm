from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.suspended_guard import SuspendedStateError
from yuantus.meta_engine.web.bom_children_router import bom_children_router
from yuantus.meta_engine.web.bom_router import bom_router
from yuantus.meta_engine.web.effectivity_router import effectivity_router
from yuantus.meta_engine.web import router as meta_router_module


def _current_user() -> CurrentUser:
    return CurrentUser(
        id=1,
        tenant_id="tenant-1",
        org_id="org-1",
        username="admin",
        email="admin@example.com",
        roles=["admin"],
        is_superuser=True,
    )


def _client_with_db(db) -> TestClient:
    app = FastAPI()
    app.include_router(bom_children_router, prefix="/api/v1")
    app.include_router(bom_router, prefix="/api/v1")
    app.include_router(effectivity_router, prefix="/api/v1")
    app.include_router(meta_router_module.meta_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = _current_user
    if meta_router_module.get_current_user:
        app.dependency_overrides[meta_router_module.get_current_user] = _current_user
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_bom_add_child_maps_not_latest_released_to_409() -> None:
    db = MagicMock()
    db.get.side_effect = lambda model, item_id: {
        "parent-1": SimpleNamespace(id="parent-1", item_type_id="Part", state="Draft"),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    client = _client_with_db(db)

    with patch("yuantus.meta_engine.web.bom_children_router.MetaPermissionService") as perm_cls, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService.add_child",
        side_effect=NotLatestReleasedError(reason="current_version_not_released", target_id="child-1"),
    ):
        perm_cls.return_value.check_permission.return_value = True
        resp = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})

    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "NOT_LATEST_RELEASED"


def test_bom_add_substitute_maps_not_latest_released_to_409() -> None:
    db = MagicMock()
    db.get.side_effect = lambda model, item_id: {
        "bom-1": SimpleNamespace(id="bom-1", item_type_id="Part BOM", source_id="parent-1"),
        "parent-1": SimpleNamespace(id="parent-1", item_type_id="Part", state="Draft"),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    client = _client_with_db(db)

    with patch("yuantus.meta_engine.web.bom_router.MetaPermissionService") as perm_cls, patch(
        "yuantus.meta_engine.web.bom_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_router.SubstituteService.add_substitute",
        side_effect=NotLatestReleasedError(reason="not_latest_released", target_id="sub-1"),
    ):
        perm_cls.return_value.check_permission.return_value = True
        resp = client.post(
            "/api/v1/bom/bom-1/substitutes",
            json={"substitute_item_id": "sub-1"},
        )

    assert resp.status_code == 409
    assert resp.json()["detail"]["reason"] == "not_latest_released"


def test_effectivity_create_maps_not_latest_released_to_409() -> None:
    client = _client_with_db(MagicMock())

    with patch(
        "yuantus.meta_engine.web.effectivity_router.EffectivityService.create_effectivity",
        side_effect=NotLatestReleasedError(reason="current_version_not_released", target_id="item-1"),
    ):
        resp = client.post(
            "/api/v1/effectivities",
            json={
                "item_id": "item-1",
                "effectivity_type": "Date",
                "start_date": "2026-04-20T00:00:00",
            },
        )

    assert resp.status_code == 409
    assert resp.json()["detail"]["target_id"] == "item-1"


def test_aml_apply_maps_not_latest_released_to_409() -> None:
    client = _client_with_db(MagicMock())

    with patch.object(
        meta_router_module.AMLEngine,
        "apply",
        side_effect=NotLatestReleasedError(
            reason="not_latest_released",
            target_id="child-1",
        ),
    ):
        resp = client.post(
            "/api/v1/aml/apply",
            json={
                "type": "Part",
                "action": "update",
                "id": "parent-1",
                "relationships": [
                    {
                        "type": "Part BOM",
                        "action": "add",
                        "properties": {"related_id": "child-1"},
                    }
                ],
            },
        )

    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "NOT_LATEST_RELEASED"


def test_bom_add_child_maps_suspended_state_to_409() -> None:
    db = MagicMock()
    db.get.side_effect = lambda model, item_id: {
        "parent-1": SimpleNamespace(id="parent-1", item_type_id="Part", state="Draft"),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    client = _client_with_db(db)

    with patch("yuantus.meta_engine.web.bom_children_router.MetaPermissionService") as perm_cls, patch(
        "yuantus.meta_engine.web.bom_children_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_children_router.BOMService.add_child",
        side_effect=SuspendedStateError(reason="target_suspended", target_id="child-1"),
    ):
        perm_cls.return_value.check_permission.return_value = True
        resp = client.post("/api/v1/bom/parent-1/children", json={"child_id": "child-1"})

    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "SUSPENDED_STATE"
    assert resp.json()["detail"]["reason"] == "target_suspended"


def test_bom_add_substitute_maps_suspended_state_to_409() -> None:
    db = MagicMock()
    db.get.side_effect = lambda model, item_id: {
        "bom-1": SimpleNamespace(id="bom-1", item_type_id="Part BOM", source_id="parent-1"),
        "parent-1": SimpleNamespace(id="parent-1", item_type_id="Part", state="Draft"),
        "Part": SimpleNamespace(id="Part"),
    }.get(item_id)
    client = _client_with_db(db)

    with patch("yuantus.meta_engine.web.bom_router.MetaPermissionService") as perm_cls, patch(
        "yuantus.meta_engine.web.bom_router.is_item_locked",
        return_value=(False, None),
    ), patch(
        "yuantus.meta_engine.web.bom_router.SubstituteService.add_substitute",
        side_effect=SuspendedStateError(reason="target_suspended", target_id="sub-1"),
    ):
        perm_cls.return_value.check_permission.return_value = True
        resp = client.post(
            "/api/v1/bom/bom-1/substitutes",
            json={"substitute_item_id": "sub-1"},
        )

    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "SUSPENDED_STATE"


def test_effectivity_create_maps_suspended_state_to_409() -> None:
    client = _client_with_db(MagicMock())

    with patch(
        "yuantus.meta_engine.web.effectivity_router.EffectivityService.create_effectivity",
        side_effect=SuspendedStateError(reason="target_suspended", target_id="item-1"),
    ):
        resp = client.post(
            "/api/v1/effectivities",
            json={
                "item_id": "item-1",
                "effectivity_type": "Date",
                "start_date": "2026-04-20T00:00:00",
            },
        )

    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "SUSPENDED_STATE"


def test_aml_apply_maps_suspended_state_to_409() -> None:
    client = _client_with_db(MagicMock())

    with patch.object(
        meta_router_module.AMLEngine,
        "apply",
        side_effect=SuspendedStateError(
            reason="target_suspended",
            target_id="child-1",
        ),
    ):
        resp = client.post(
            "/api/v1/aml/apply",
            json={
                "type": "Part",
                "action": "update",
                "id": "parent-1",
                "relationships": [
                    {
                        "type": "Part BOM",
                        "action": "add",
                        "properties": {"related_id": "child-1"},
                    }
                ],
            },
        )

    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "SUSPENDED_STATE"
