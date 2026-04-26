from __future__ import annotations

import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_401_UNAUTHORIZED

from yuantus.api.app import create_app
from yuantus.api.middleware.request_logging import RequestLoggingMiddleware
from yuantus.config import get_settings
from yuantus.context import (
    org_id_var,
    request_id_var,
    tenant_id_var,
    user_id_var,
)


class _InjectFixedIdentityMiddleware(BaseHTTPMiddleware):
    """Mimics auth/context middleware: sets all three identity ContextVars,
    snapshots to request.state, and resets in finally — exactly the lifetime
    pattern that caused the original bug class."""

    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_token = tenant_id_var.set("T1")
        org_token = org_id_var.set("O1")
        user_token = user_id_var.set("U99")
        request.state.tenant_id = "T1"
        request.state.org_id = "O1"
        request.state.user_id = "U99"
        try:
            return await call_next(request)
        finally:
            user_id_var.reset(user_token)
            org_id_var.reset(org_token)
            tenant_id_var.reset(tenant_token)


class _AuthShortCircuit401Middleware(BaseHTTPMiddleware):
    """Mimics AuthEnforcementMiddleware short-circuiting before any context is
    set — verifies the log line still emits with status_code=401 and identity
    fields = None."""

    async def dispatch(self, request: Request, call_next) -> Response:
        return JSONResponse({"detail": "denied"}, status_code=HTTP_401_UNAUTHORIZED)


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


def test_chain_log_carries_tenant_org_user_after_inner_resets_contextvars(caplog) -> None:
    """Regression for 2026-04-26 bug: outermost RequestLoggingMiddleware was
    reading ContextVars in its finally — but inner middleware had already
    reset them, so log lines carried tenant_id/org_id/user_id always = None.
    Fix contract: read from request.state, which inner middleware snapshots
    to before reset."""
    settings = get_settings()
    original = settings.LOG_FORMAT
    settings.LOG_FORMAT = "json"
    try:
        app = FastAPI()
        app.add_middleware(_InjectFixedIdentityMiddleware)
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/echo")
        def echo() -> dict:
            return {"ok": True}

        client = TestClient(app)
        with caplog.at_level(logging.INFO, logger="yuantus.request"):
            client.get("/echo")

        records = []
        for rec in caplog.records:
            try:
                records.append(json.loads(rec.message))
            except (json.JSONDecodeError, TypeError):
                continue
        assert records, "expected JSON log record"
        record = records[-1]
        assert record["tenant_id"] == "T1", record
        assert record["org_id"] == "O1", record
        assert record["user_id"] == "U99", record
        assert record["status_code"] == 200
    finally:
        settings.LOG_FORMAT = original


def test_chain_log_carries_tenant_org_user_in_text_format(caplog) -> None:
    settings = get_settings()
    original = settings.LOG_FORMAT
    settings.LOG_FORMAT = "text"
    try:
        app = FastAPI()
        app.add_middleware(_InjectFixedIdentityMiddleware)
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/echo")
        def echo() -> dict:
            return {"ok": True}

        client = TestClient(app)
        with caplog.at_level(logging.INFO, logger="yuantus.request"):
            client.get("/echo")

        msg = next(r.message for r in caplog.records)
        assert "tenant_id=T1" in msg, msg
        assert "org_id=O1" in msg, msg
        assert "user_id=U99" in msg, msg
    finally:
        settings.LOG_FORMAT = original


def test_text_log_emits_fixed_field_set_even_when_values_are_none(caplog) -> None:
    """Plan §6 acceptance: 'every API request log line contains the fixed
    field set'. Original text format dropped None-valued keys; this contract
    asserts every required key is present even when the value is None."""
    settings = get_settings()
    original = settings.LOG_FORMAT
    settings.LOG_FORMAT = "text"
    try:
        app = _build_minimal_app()
        client = TestClient(app)
        with caplog.at_level(logging.INFO, logger="yuantus.request"):
            client.get("/echo")

        msg = next(r.message for r in caplog.records)
        for key in (
            "request_id",
            "tenant_id",
            "org_id",
            "user_id",
            "method",
            "path",
            "status_code",
            "latency_ms",
        ):
            assert f"{key}=" in msg, f"text log missing field {key!r}: {msg!r}"
    finally:
        settings.LOG_FORMAT = original


def test_log_emits_for_auth_short_circuit_with_none_identity(caplog) -> None:
    """When AuthEnforcementMiddleware returns 401 before any identity context
    is set, the log line must still emit (with status_code=401 and identity
    fields = None) so denied requests are observable."""
    settings = get_settings()
    original = settings.LOG_FORMAT
    settings.LOG_FORMAT = "json"
    try:
        app = FastAPI()
        app.add_middleware(_AuthShortCircuit401Middleware)
        app.add_middleware(RequestLoggingMiddleware)

        @app.get("/echo")
        def echo() -> dict:
            return {"ok": True}

        client = TestClient(app)
        with caplog.at_level(logging.INFO, logger="yuantus.request"):
            response = client.get("/echo")

        assert response.status_code == 401
        records = []
        for rec in caplog.records:
            try:
                records.append(json.loads(rec.message))
            except (json.JSONDecodeError, TypeError):
                continue
        assert records, "expected JSON log record even on 401"
        record = records[-1]
        assert record["status_code"] == 401
        assert record["tenant_id"] is None
        assert record["org_id"] is None
        assert record["user_id"] is None
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
