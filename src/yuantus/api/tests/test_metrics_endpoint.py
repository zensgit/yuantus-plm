from __future__ import annotations

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.observability.metrics import record_job_lifecycle, reset_registry


def setup_function(_fn) -> None:
    reset_registry()
    get_settings().METRICS_ENABLED = True


def test_metrics_endpoint_returns_200_with_prometheus_content_type() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_endpoint_serves_recorded_data() -> None:
    record_job_lifecycle("cad_convert", "success", 250.0)
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/metrics")
    body = response.text
    assert 'yuantus_jobs_total{task_type="cad_convert",status="success"} 1' in body
    assert 'yuantus_job_duration_ms_bucket{task_type="cad_convert",status="success",le="500"} 1' in body


def test_metrics_endpoint_returns_404_when_disabled() -> None:
    settings = get_settings()
    original = settings.METRICS_ENABLED
    settings.METRICS_ENABLED = False
    try:
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/metrics")
        assert response.status_code == 404
    finally:
        settings.METRICS_ENABLED = original


def test_instrumentation_records_even_when_endpoint_disabled() -> None:
    settings = get_settings()
    original = settings.METRICS_ENABLED
    settings.METRICS_ENABLED = False
    try:
        record_job_lifecycle("cad_convert", "success", 100.0)
        settings.METRICS_ENABLED = True
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert 'yuantus_jobs_total{task_type="cad_convert",status="success"} 1' in response.text
    finally:
        settings.METRICS_ENABLED = original


def test_metrics_route_is_registered_in_app() -> None:
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/v1/metrics" in paths


def test_metrics_endpoint_empty_job_registry_returns_runtime_search_indexer_metrics() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "yuantus_jobs_total" not in response.text
    assert "yuantus_search_indexer_registered" in response.text
    assert "yuantus_search_indexer_events_total" in response.text
