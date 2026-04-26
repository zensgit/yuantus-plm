from __future__ import annotations

import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.middleware.request_logging import RequestLoggingMiddleware
from yuantus.config import get_settings
from yuantus.context import request_id_var


def _build_minimal_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/echo")
    def echo() -> dict:
        return {"request_id": request_id_var.get()}

    return app


def test_request_logging_middleware_is_registered_in_app() -> None:
    app = create_app()
    classes = {m.cls.__name__ for m in app.user_middleware}
    assert "RequestLoggingMiddleware" in classes


def test_response_carries_request_id_header_when_absent_from_request() -> None:
    app = _build_minimal_app()
    client = TestClient(app)

    response = client.get("/echo")

    header_name = get_settings().REQUEST_ID_HEADER
    assert response.status_code == 200
    assert response.headers.get(header_name)
    assert response.json()["request_id"] == response.headers[header_name]


def test_request_id_passthrough_when_supplied_via_header() -> None:
    app = _build_minimal_app()
    client = TestClient(app)
    upstream_id = "abc-123-upstream"

    header_name = get_settings().REQUEST_ID_HEADER
    response = client.get("/echo", headers={header_name: upstream_id})

    assert response.status_code == 200
    assert response.headers[header_name] == upstream_id
    assert response.json()["request_id"] == upstream_id


def test_request_id_var_is_reset_after_response() -> None:
    app = _build_minimal_app()
    client = TestClient(app)

    response = client.get("/echo")
    assert response.status_code == 200
    assert request_id_var.get() is None


def test_log_format_text_emits_kv_line(caplog) -> None:
    settings = get_settings()
    original = settings.LOG_FORMAT
    settings.LOG_FORMAT = "text"
    try:
        app = _build_minimal_app()
        client = TestClient(app)
        with caplog.at_level(logging.INFO, logger="yuantus.request"):
            client.get("/echo")

        assert any(
            "method=GET" in rec.message and "path=/echo" in rec.message
            for rec in caplog.records
        )
    finally:
        settings.LOG_FORMAT = original


def test_log_format_json_emits_json_payload(caplog) -> None:
    settings = get_settings()
    original = settings.LOG_FORMAT
    settings.LOG_FORMAT = "json"
    try:
        app = _build_minimal_app()
        client = TestClient(app)
        with caplog.at_level(logging.INFO, logger="yuantus.request"):
            client.get("/echo")

        json_records = []
        for rec in caplog.records:
            try:
                json_records.append(json.loads(rec.message))
            except (json.JSONDecodeError, TypeError):
                continue

        assert json_records, "expected at least one JSON log record"
        record = json_records[-1]
        assert record["method"] == "GET"
        assert record["path"] == "/echo"
        assert record["status_code"] == 200
        assert "latency_ms" in record
        assert "request_id" in record
    finally:
        settings.LOG_FORMAT = original


def test_required_log_fields_are_emitted(caplog) -> None:
    settings = get_settings()
    original = settings.LOG_FORMAT
    settings.LOG_FORMAT = "json"
    try:
        app = _build_minimal_app()
        client = TestClient(app)
        with caplog.at_level(logging.INFO, logger="yuantus.request"):
            client.get("/echo")

        json_records = []
        for rec in caplog.records:
            try:
                json_records.append(json.loads(rec.message))
            except (json.JSONDecodeError, TypeError):
                continue

        assert json_records
        record = json_records[-1]
        for required in (
            "request_id",
            "method",
            "path",
            "status_code",
            "latency_ms",
        ):
            assert required in record, f"missing required field {required!r}"
    finally:
        settings.LOG_FORMAT = original
