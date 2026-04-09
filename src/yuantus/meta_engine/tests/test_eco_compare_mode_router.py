"""Tests for ECO compare_mode contract on impact, bom-diff, and compute-changes endpoints."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user, get_current_user_id_optional
from yuantus.database import get_db


def _client_with_user():
    mock_db = MagicMock()
    user = SimpleNamespace(id=1, roles=["admin"])

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_user_id_optional] = lambda: 1
    return TestClient(app), mock_db


def _mock_eco(product_id="prod-1"):
    return SimpleNamespace(
        id="eco-1",
        product_id=product_id,
        name="Test ECO",
        state="in_review",
    )


def _mock_product():
    return SimpleNamespace(id="prod-1", item_type_id="Part")


# ── impact: compare_mode pass-through ──


def test_impact_passes_compare_mode_to_service():
    client, db = _client_with_user()
    eco = _mock_eco()
    product = _mock_product()
    db.get.return_value = product

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        with patch("yuantus.meta_engine.web.eco_router.MetaPermissionService") as perm_cls:
            perm_cls.return_value.check_permission.return_value = True
            svc_cls.return_value.get_eco.return_value = eco
            svc_cls.return_value.analyze_impact.return_value = {"changes": []}
            resp = client.get(
                "/api/v1/eco/eco-1/impact",
                params={"compare_mode": "by_item"},
            )

    assert resp.status_code == 200
    svc_cls.return_value.analyze_impact.assert_called_once()
    call_kwargs = svc_cls.return_value.analyze_impact.call_args[1]
    assert call_kwargs["compare_mode"] == "by_item"


def test_impact_invalid_compare_mode_returns_400():
    client, db = _client_with_user()
    eco = _mock_eco()
    product = _mock_product()
    db.get.return_value = product

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        with patch("yuantus.meta_engine.web.eco_router.MetaPermissionService") as perm_cls:
            perm_cls.return_value.check_permission.return_value = True
            svc_cls.return_value.get_eco.return_value = eco
            svc_cls.return_value.analyze_impact.side_effect = ValueError(
                "Invalid compare_mode: invalid_mode"
            )
            resp = client.get(
                "/api/v1/eco/eco-1/impact",
                params={"compare_mode": "invalid_mode"},
            )

    assert resp.status_code == 400
    assert "invalid_mode" in resp.json()["detail"]


# ── impact/export: compare_mode pass-through ──


def test_impact_export_passes_compare_mode_to_service():
    client, db = _client_with_user()
    eco = _mock_eco()
    product = _mock_product()
    db.get.return_value = product

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        with patch("yuantus.meta_engine.web.eco_router.MetaPermissionService") as perm_cls:
            perm_cls.return_value.check_permission.return_value = True
            svc_cls.return_value.get_eco.return_value = eco
            svc_cls.return_value.analyze_impact.return_value = {"changes": []}
            resp = client.get(
                "/api/v1/eco/eco-1/impact/export",
                params={"format": "json", "compare_mode": "summarized"},
            )

    assert resp.status_code == 200
    svc_cls.return_value.analyze_impact.assert_called_once()
    call_kwargs = svc_cls.return_value.analyze_impact.call_args[1]
    assert call_kwargs["compare_mode"] == "summarized"


# ── bom-diff: compare_mode pass-through ──


def test_bom_diff_passes_compare_mode_to_service():
    client, db = _client_with_user()
    eco = _mock_eco()
    product = _mock_product()
    db.get.return_value = product

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        with patch("yuantus.meta_engine.web.eco_router.MetaPermissionService") as perm_cls:
            perm_cls.return_value.check_permission.return_value = True
            svc_cls.return_value.get_eco.return_value = eco
            svc_cls.return_value.get_bom_diff.return_value = {"diff": []}
            resp = client.get(
                "/api/v1/eco/eco-1/bom-diff",
                params={"compare_mode": "by_position"},
            )

    assert resp.status_code == 200
    svc_cls.return_value.get_bom_diff.assert_called_once()
    call_kwargs = svc_cls.return_value.get_bom_diff.call_args[1]
    assert call_kwargs["compare_mode"] == "by_position"


def test_bom_diff_invalid_compare_mode_returns_400():
    client, db = _client_with_user()
    eco = _mock_eco()
    product = _mock_product()
    db.get.return_value = product

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        with patch("yuantus.meta_engine.web.eco_router.MetaPermissionService") as perm_cls:
            perm_cls.return_value.check_permission.return_value = True
            svc_cls.return_value.get_eco.return_value = eco
            svc_cls.return_value.get_bom_diff.side_effect = ValueError(
                "Invalid compare_mode: bad_mode"
            )
            resp = client.get(
                "/api/v1/eco/eco-1/bom-diff",
                params={"compare_mode": "bad_mode"},
            )

    assert resp.status_code == 400
    assert "bad_mode" in resp.json()["detail"]


# ── compute-changes: compare_mode pass-through ──


def test_compute_changes_passes_compare_mode_to_service():
    client, db = _client_with_user()

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        change = SimpleNamespace(to_dict=lambda: {"id": "ch-1", "change_type": "add"})
        svc_cls.return_value.compute_bom_changes.return_value = [change]
        resp = client.post(
            "/api/v1/eco/eco-1/compute-changes",
            params={"compare_mode": "num_qty"},
        )

    assert resp.status_code == 200
    svc_cls.return_value.compute_bom_changes.assert_called_once_with(
        "eco-1", compare_mode="num_qty"
    )


def test_compute_changes_invalid_compare_mode_returns_400():
    client, db = _client_with_user()

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        svc_cls.return_value.compute_bom_changes.side_effect = ValueError(
            "Invalid compare_mode: wrong"
        )
        resp = client.post(
            "/api/v1/eco/eco-1/compute-changes",
            params={"compare_mode": "wrong"},
        )

    assert resp.status_code == 400
    assert "wrong" in resp.json()["detail"]


def test_compute_changes_none_compare_mode_uses_default():
    client, db = _client_with_user()

    with patch("yuantus.meta_engine.web.eco_router.ECOService") as svc_cls:
        change = SimpleNamespace(to_dict=lambda: {"id": "ch-1", "change_type": "add"})
        svc_cls.return_value.compute_bom_changes.return_value = [change]
        resp = client.post("/api/v1/eco/eco-1/compute-changes")

    assert resp.status_code == 200
    svc_cls.return_value.compute_bom_changes.assert_called_once_with(
        "eco-1", compare_mode=None
    )
