from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.database import get_db


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _client():
    app = create_app()
    db = MagicMock()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), db


def _stage(**overrides):
    stage = MagicMock()
    stage.id = overrides.get("id", "stage-1")
    stage.name = overrides.get("name", "Review")
    stage.sequence = overrides.get("sequence", 10)
    stage.approval_type = overrides.get("approval_type", "mandatory")
    stage.approval_roles = overrides.get("approval_roles", ["engineer"])
    stage.sla_hours = overrides.get("sla_hours", 24)
    stage.is_blocking = overrides.get("is_blocking", True)
    stage.auto_progress = overrides.get("auto_progress", False)
    stage.fold = overrides.get("fold", False)
    stage.description = overrides.get("description", "Review stage")
    return stage


def test_list_stages_returns_existing_response_shape() -> None:
    client, _db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.list_stages.return_value = [_stage()]
        resp = client.get("/api/v1/eco/stages")

    assert resp.status_code == 200
    body = resp.json()
    assert body == [
        {
            "id": "stage-1",
            "name": "Review",
            "sequence": 10,
            "approval_type": "mandatory",
            "approval_roles": ["engineer"],
            "sla_hours": 24,
            "is_blocking": True,
            "auto_progress": False,
            "fold": False,
            "description": "Review stage",
        }
    ]


def test_create_stage_commits_and_returns_compact_shape() -> None:
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.create_stage.return_value = _stage(name="QA")
        resp = client.post(
            "/api/v1/eco/stages",
            json={
                "name": "QA",
                "sequence": 20,
                "approval_type": "optional",
                "approval_roles": ["qa"],
                "is_blocking": False,
                "auto_progress": True,
                "sla_hours": 8,
                "description": "QA gate",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {
        "id": "stage-1",
        "name": "QA",
        "sequence": 10,
        "approval_type": "mandatory",
        "sla_hours": 24,
    }
    service_cls.return_value.create_stage.assert_called_once_with(
        name="QA",
        sequence=20,
        approval_type="optional",
        approval_roles=["qa"],
        is_blocking=False,
        auto_progress=True,
        sla_hours=8,
        description="QA gate",
    )
    db.commit.assert_called_once()


def test_create_stage_rolls_back_on_service_error() -> None:
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.create_stage.side_effect = RuntimeError("boom")
        resp = client.post("/api/v1/eco/stages", json={"name": "QA"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "boom"
    db.rollback.assert_called_once()


def test_update_stage_forwards_unset_excluded_payload() -> None:
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.update_stage.return_value = _stage(name="Updated")
        resp = client.put("/api/v1/eco/stages/stage-1", json={"name": "Updated"})

    assert resp.status_code == 200
    service_cls.return_value.update_stage.assert_called_once_with(
        "stage-1",
        name="Updated",
    )
    db.commit.assert_called_once()


def test_update_stage_maps_value_error_to_404() -> None:
    client, _db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.update_stage.side_effect = ValueError("Stage not found")
        resp = client.put("/api/v1/eco/stages/no-such", json={"name": "Missing"})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Stage not found"


def test_delete_stage_success_commits() -> None:
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.delete_stage.return_value = True
        resp = client.delete("/api/v1/eco/stages/stage-1")

    assert resp.status_code == 200
    assert resp.json() == {"success": True, "message": "Stage deleted"}
    service_cls.return_value.delete_stage.assert_called_once_with("stage-1")
    db.commit.assert_called_once()


def test_delete_stage_false_maps_to_404() -> None:
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.delete_stage.return_value = False
        resp = client.delete("/api/v1/eco/stages/no-such")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Stage not found"
    db.rollback.assert_not_called()


def test_delete_stage_unexpected_error_rolls_back() -> None:
    client, db = _client()

    with patch("yuantus.meta_engine.web.eco_stage_router.ECOStageService") as service_cls:
        service_cls.return_value.delete_stage.side_effect = RuntimeError("boom")
        resp = client.delete("/api/v1/eco/stages/stage-1")

    assert resp.status_code == 500
    assert resp.json()["detail"] == "boom"
    db.rollback.assert_called_once()
