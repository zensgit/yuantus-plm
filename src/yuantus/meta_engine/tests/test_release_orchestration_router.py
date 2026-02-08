from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


def test_plan_denies_non_admin():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    resp = client.get("/api/v1/release-orchestration/items/item-1/plan")
    assert resp.status_code == 403


def test_execute_denies_non_admin():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client, _db = _client_with_user(user)

    resp = client.post("/api/v1/release-orchestration/items/item-1/execute", json={})
    assert resp.status_code == 403


def test_plan_returns_steps_with_actions():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    db.get.return_value = Item(
        id="item-1",
        item_type_id="Part",
        config_id="CFG-1",
        generation=1,
        state="released",
        properties={"item_number": "P-1"},
    )

    payload = {
        "item_id": "item-1",
        "generated_at": "2026-02-07T00:00:00Z",
        "ruleset_id": "default",
        "summary": {
            "ok": False,
            "resources": 3,
            "ok_resources": 2,
            "error_count": 1,
            "warning_count": 0,
            "by_kind": {},
        },
        "resources": [
            {
                "kind": "routing_release",
                "resource_type": "routing",
                "resource_id": "routing-1",
                "name": "R-1",
                "state": "draft",
                "ruleset_id": "default",
                "errors": [],
                "warnings": [],
            },
            {
                "kind": "mbom_release",
                "resource_type": "mbom",
                "resource_id": "mbom-1",
                "name": "M-1",
                "state": "released",
                "ruleset_id": "default",
                "errors": [],
                "warnings": [],
            },
            {
                "kind": "baseline_release",
                "resource_type": "baseline",
                "resource_id": "baseline-1",
                "name": "B-1",
                "state": "draft",
                "ruleset_id": "default",
                "errors": [
                    {
                        "code": "baseline_member_missing_item",
                        "message": "missing",
                        "rule_id": "baseline.members_references_exist",
                        "details": {"baseline_id": "baseline-1"},
                    }
                ],
                "warnings": [],
            },
        ],
        "esign_manifest": None,
    }

    with patch(
        "yuantus.meta_engine.web.release_orchestration_router.ReleaseReadinessService.get_item_release_readiness"
    ) as mocked:
        mocked.return_value = payload
        resp = client.get("/api/v1/release-orchestration/items/item-1/plan?ruleset_id=default")

    assert resp.status_code == 200
    data = resp.json()
    assert data["item_id"] == "item-1"
    assert data["ruleset_id"] == "default"

    steps = data.get("steps") or []
    assert len(steps) == 3
    actions = {s["resource_id"]: s["action"] for s in steps}
    assert actions["routing-1"] == "release"
    assert actions["mbom-1"] == "skip_already_released"
    assert actions["baseline-1"] == "skip_errors"


def test_execute_dry_run_does_not_call_release():
    user = SimpleNamespace(id=1, roles=["admin"], is_superuser=False)
    client, db = _client_with_user(user)

    db.get.return_value = Item(
        id="item-1",
        item_type_id="Part",
        config_id="CFG-1",
        generation=1,
        state="released",
        properties={"item_number": "P-1"},
    )

    routing = SimpleNamespace(id="routing-1", state="draft")
    mbom = SimpleNamespace(id="mbom-1", state="draft")
    baseline = SimpleNamespace(id="baseline-1", state="draft")

    with (
        patch("yuantus.meta_engine.web.release_orchestration_router.ReleaseReadinessService") as rr_cls,
        patch("yuantus.meta_engine.web.release_orchestration_router.RoutingService") as routing_cls,
        patch("yuantus.meta_engine.web.release_orchestration_router.MBOMService") as mbom_cls,
        patch("yuantus.meta_engine.web.release_orchestration_router.BaselineService") as baseline_cls,
    ):
        rr = rr_cls.return_value
        rr.list_mboms.return_value = [mbom]
        rr.list_routings.return_value = [routing]
        rr.list_baselines.return_value = [baseline]
        rr.get_item_release_readiness.return_value = {
            "item_id": "item-1",
            "generated_at": "2026-02-07T00:00:00Z",
            "ruleset_id": "default",
            "summary": {"ok": True},
            "resources": [],
        }

        routing_svc = routing_cls.return_value
        routing_svc.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [],
            "warnings": [],
        }

        mbom_svc = mbom_cls.return_value
        mbom_svc.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [],
            "warnings": [],
        }

        baseline_svc = baseline_cls.return_value
        baseline_svc.get_release_diagnostics.return_value = {
            "ruleset_id": "default",
            "errors": [],
            "warnings": [],
        }

        resp = client.post(
            "/api/v1/release-orchestration/items/item-1/execute",
            json={
                "dry_run": True,
                "include_routings": True,
                "include_mboms": True,
                "include_baselines": True,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        statuses = {r["resource_id"]: r["status"] for r in (data.get("results") or [])}
        assert statuses["routing-1"] == "planned"
        assert statuses["mbom-1"] == "planned"
        assert statuses["baseline-1"] == "planned"

        routing_svc.release_routing.assert_not_called()
        mbom_svc.release_mbom.assert_not_called()
        baseline_svc.release_baseline.assert_not_called()

