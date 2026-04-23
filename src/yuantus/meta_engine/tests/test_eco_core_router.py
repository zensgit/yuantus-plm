from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.eco import ECOState


@pytest.fixture(autouse=True)
def _auth_optional(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client():
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = lambda: 1
    return TestClient(app), mock_db


def _eco(**overrides):
    data = {"id": "eco-1", "name": "ECO-1", "state": ECOState.DRAFT.value}
    data.update(overrides)
    return SimpleNamespace(**data, to_dict=lambda: data)


def test_kanban_endpoint_returns_stages_and_ecos_by_stage():
    client, _db = _client()
    stage = SimpleNamespace(
        id="stage-1",
        name="Review",
        sequence=10,
        fold=False,
        approval_type="parallel",
        sla_hours=24,
    )

    with (
        patch("yuantus.meta_engine.web.eco_core_router.ECOStageService") as stage_cls,
        patch("yuantus.meta_engine.web.eco_core_router.ECOService") as eco_cls,
    ):
        stage_cls.return_value.list_stages.return_value = [stage]
        eco_cls.return_value.list_ecos.return_value = [_eco(id="eco-1", stage_id="stage-1")]
        resp = client.get("/api/v1/eco/kanban", params={"product_id": "prod-1"})

    assert resp.status_code == 200
    assert resp.json()["stages"][0]["id"] == "stage-1"
    assert resp.json()["ecos_by_stage"]["stage-1"][0]["id"] == "eco-1"
    eco_cls.return_value.list_ecos.assert_called_once_with(
        stage_id="stage-1",
        product_id="prod-1",
    )


def test_create_eco_endpoint_commits_and_returns_eco():
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.create_eco.return_value = _eco(id="eco-created", name="Created")
        resp = client.post(
            "/api/v1/eco",
            json={
                "name": "Created",
                "eco_type": "bom",
                "product_id": "prod-1",
                "description": "desc",
                "priority": "high",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["id"] == "eco-created"
    assert db.commit.called
    service.create_eco.assert_called_once_with(
        name="Created",
        eco_type="bom",
        product_id="prod-1",
        description="desc",
        priority="high",
        user_id=1,
    )


def test_list_ecos_endpoint_passes_filters():
    client, _db = _client()

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.list_ecos.return_value = [_eco(id="eco-1")]
        resp = client.get(
            "/api/v1/eco",
            params={
                "state": "draft",
                "stage_id": "stage-1",
                "product_id": "prod-1",
                "created_by_id": 7,
                "limit": 25,
                "offset": 5,
            },
        )

    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "eco-1"
    service.list_ecos.assert_called_once_with(
        state="draft",
        stage_id="stage-1",
        product_id="prod-1",
        created_by_id=7,
        limit=25,
        offset=5,
    )


def test_get_eco_endpoint_404_when_missing():
    client, _db = _client()

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service_cls.return_value.get_eco.return_value = None
        resp = client.get("/api/v1/eco/missing")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "ECO not found"


def test_bind_product_endpoint_commits_and_returns_eco():
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.bind_product.return_value = _eco(id="eco-1", product_id="prod-1")
        resp = client.post(
            "/api/v1/eco/eco-1/bind-product",
            json={"product_id": "prod-1", "create_target_revision": True},
        )

    assert resp.status_code == 200
    assert resp.json()["product_id"] == "prod-1"
    assert db.commit.called
    service.bind_product.assert_called_once_with(
        "eco-1",
        "prod-1",
        1,
        create_target_revision=True,
    )


def test_update_eco_endpoint_rejects_empty_body():
    client, _db = _client()

    resp = client.put("/api/v1/eco/eco-1", json={})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "No fields provided for update"


def test_update_eco_endpoint_commits_and_returns_eco():
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.update_eco.return_value = _eco(id="eco-1", priority="high")
        resp = client.put("/api/v1/eco/eco-1", json={"priority": "high"})

    assert resp.status_code == 200
    assert resp.json()["priority"] == "high"
    assert db.commit.called
    service.update_eco.assert_called_once_with("eco-1", {"priority": "high"}, 1)


def test_delete_eco_endpoint_rejects_non_draft_state():
    client, _db = _client()

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service_cls.return_value.get_eco.return_value = _eco(state=ECOState.DONE.value)
        resp = client.delete("/api/v1/eco/eco-1")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Can only delete ECOs in draft state"


def test_delete_eco_endpoint_deletes_draft_eco():
    client, db = _client()
    eco = _eco()

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service_cls.return_value.get_eco.return_value = eco
        resp = client.delete("/api/v1/eco/eco-1")

    assert resp.status_code == 200
    assert resp.json() == {"success": True, "message": "ECO deleted"}
    db.delete.assert_called_once_with(eco)
    assert db.commit.called


def test_new_revision_endpoint_commits_and_returns_version():
    client, db = _client()
    version = SimpleNamespace(id="ver-1", version_label="B")

    with patch("yuantus.meta_engine.web.eco_core_router.ECOService") as service_cls:
        service = service_cls.return_value
        service.action_new_revision.return_value = version
        resp = client.post("/api/v1/eco/eco-1/new-revision")

    assert resp.status_code == 200
    assert resp.json() == {
        "success": True,
        "version_id": "ver-1",
        "version_label": "B",
    }
    assert db.commit.called
    service.action_new_revision.assert_called_once_with("eco-1", 1)
