"""Tests for C16 – Quality analytics router."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.database import get_db
from yuantus.meta_engine.web.quality_analytics_router import quality_analytics_router


def _client_with_db():
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = FastAPI()
    app.include_router(quality_analytics_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), mock_db


def _mock_check(**overrides):
    defaults = {
        "id": "chk-1",
        "point_id": "pt-1",
        "result": "pass",
        "measure_value": 10.0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _mock_alert(**overrides):
    defaults = {
        "id": "alt-1",
        "state": "new",
        "check_id": "chk-1",
        "priority": "medium",
        "created_at": datetime(2026, 3, 1),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _mock_point(**overrides):
    defaults = {
        "id": "pt-1",
        "name": "Torque Check",
        "measure_min": 9.0,
        "measure_max": 11.0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_full_analytics_endpoint():
    client, _ = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_analytics_router.QualityService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_checks.return_value = [_mock_check()]
        svc.list_alerts.return_value = [_mock_alert()]
        svc.list_points.return_value = [_mock_point()]

        resp = client.get("/api/v1/quality/analytics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["report"] == "quality-analytics"
    assert "defect_rates" in data


def test_defect_rates_endpoint():
    client, _ = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_analytics_router.QualityService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_checks.return_value = [_mock_check()]
        svc.list_alerts.return_value = []
        svc.list_points.return_value = [_mock_point()]

        resp = client.get("/api/v1/quality/analytics/defect-rates")

    assert resp.status_code == 200
    assert "points" in resp.json()


def test_alert_aging_endpoint():
    client, _ = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_analytics_router.QualityService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_checks.return_value = []
        svc.list_alerts.return_value = [_mock_alert()]
        svc.list_points.return_value = []

        resp = client.get("/api/v1/quality/analytics/alert-aging")

    assert resp.status_code == 200
    assert "total_open" in resp.json()


def test_spc_from_payload():
    client, _ = _client_with_db()
    payload = {
        "measurements": [10.0, 10.1, 9.9, 10.0, 10.05],
        "lsl": 9.0,
        "usl": 11.0,
    }

    resp = client.post("/api/v1/quality/spc", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert "capability" in data
    assert "control_chart" in data
    assert "out_of_control" in data


def test_spc_from_point():
    client, _ = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_analytics_router.QualityService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_point.return_value = _mock_point()
        svc.list_checks.return_value = [
            _mock_check(measure_value=10.0),
            _mock_check(measure_value=10.1),
            _mock_check(measure_value=9.9),
        ]

        resp = client.get("/api/v1/quality/spc/pt-1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["point_id"] == "pt-1"
    assert "capability" in data


def test_spc_from_point_not_found():
    client, _ = _client_with_db()

    with patch("yuantus.meta_engine.web.quality_analytics_router.QualityService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_point.return_value = None

        resp = client.get("/api/v1/quality/spc/nonexistent")

    assert resp.status_code == 200
    assert resp.json()["error"] == "Point nonexistent not found"


def test_spc_payload_empty_measurements():
    client, _ = _client_with_db()
    payload = {"measurements": [], "lsl": 0.0, "usl": 10.0}

    resp = client.post("/api/v1/quality/spc", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["capability"]["sample_size"] == 0


def test_quality_analytics_routes_registered_in_create_app():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/quality/analytics" in paths
    assert "/api/v1/quality/analytics/defect-rates" in paths
    assert "/api/v1/quality/analytics/alert-aging" in paths
    assert "/api/v1/quality/spc" in paths
    assert "/api/v1/quality/spc/{point_id}" in paths
