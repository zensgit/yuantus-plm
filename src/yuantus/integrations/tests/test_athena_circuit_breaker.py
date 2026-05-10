from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx
import pytest

from yuantus.integrations import circuit_breaker as breaker_mod
from yuantus.integrations.circuit_breaker import CLOSED, OPEN, CircuitOpenError
from yuantus.integrations.athena import (
    ATHENA_BREAKER_NAME,
    AthenaClient,
    build_athena_breaker,
)


def _force_breaker_with(monkeypatch, **overrides):
    """Replace the registered athena breaker with one built from overridden
    settings, using `monkeypatch` for auto-restoring per-attribute writes."""
    from yuantus.config import get_settings

    breaker_mod.reset_registry()
    settings = get_settings()
    for key, value in overrides.items():
        monkeypatch.setattr(settings, key, value)
    return build_athena_breaker()


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    response = httpx.Response(
        status_code=status_code, request=httpx.Request("GET", "http://x")
    )
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=response.request, response=response
    )


def test_breaker_name_is_stable():
    assert ATHENA_BREAKER_NAME == "athena"


def test_default_off_is_passthrough(monkeypatch):
    breaker_mod.reset_registry()
    breaker = _force_breaker_with(monkeypatch, CIRCUIT_BREAKER_ATHENA_ENABLED=False)
    try:
        assert breaker.enabled is False
        client = AthenaClient()
        with patch.object(
            client, "_health_inner", side_effect=httpx.ConnectError("boom")
        ):
            with pytest.raises(httpx.ConnectError):
                asyncio.run(client.health())
        snapshot = breaker.status()
        assert snapshot["state"] == CLOSED
        assert snapshot["failures_total"] == 0
    finally:
        breaker_mod.reset_registry()


def test_enabled_breaker_opens_after_repeated_request_errors(monkeypatch):
    breaker_mod.reset_registry()
    breaker = _force_breaker_with(
        monkeypatch,
        CIRCUIT_BREAKER_ATHENA_ENABLED=True,
        CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD=3,
    )
    try:
        client = AthenaClient()
        with patch.object(
            client, "_health_inner", side_effect=httpx.ConnectError("upstream")
        ):
            for _ in range(3):
                with pytest.raises(httpx.ConnectError):
                    asyncio.run(client.health())
        assert breaker.status()["state"] == OPEN
        with patch.object(
            client, "_health_inner", side_effect=AssertionError("must not be called")
        ):
            with pytest.raises(CircuitOpenError):
                asyncio.run(client.health())
    finally:
        breaker_mod.reset_registry()


def test_5xx_server_errors_trip_breaker(monkeypatch):
    breaker_mod.reset_registry()
    breaker = _force_breaker_with(
        monkeypatch,
        CIRCUIT_BREAKER_ATHENA_ENABLED=True,
        CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD=3,
    )
    try:
        client = AthenaClient()
        for status in (500, 502, 503):
            err = _http_status_error(status)
            with patch.object(client, "_health_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    asyncio.run(client.health())
        assert breaker.status()["state"] == OPEN
    finally:
        breaker_mod.reset_registry()


def test_408_and_429_are_counted_as_breaker_failures(monkeypatch):
    breaker_mod.reset_registry()
    breaker = _force_breaker_with(
        monkeypatch,
        CIRCUIT_BREAKER_ATHENA_ENABLED=True,
        CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD=2,
    )
    try:
        client = AthenaClient()
        for status in (408, 429):
            err = _http_status_error(status)
            with patch.object(client, "_health_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    asyncio.run(client.health())
        assert breaker.status()["state"] == OPEN
    finally:
        breaker_mod.reset_registry()


def test_4xx_client_errors_do_not_trip_breaker(monkeypatch):
    breaker_mod.reset_registry()
    breaker = _force_breaker_with(
        monkeypatch,
        CIRCUIT_BREAKER_ATHENA_ENABLED=True,
        CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD=2,
    )
    try:
        client = AthenaClient()
        for status in (400, 401, 403, 404, 422):
            err = _http_status_error(status)
            with patch.object(client, "_health_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    asyncio.run(client.health())
        snap = breaker.status()
        assert snap["state"] == CLOSED
        assert snap["failures_total"] == 0
    finally:
        breaker_mod.reset_registry()


def test_os_error_does_not_trip_breaker(monkeypatch):
    breaker_mod.reset_registry()
    breaker = _force_breaker_with(
        monkeypatch,
        CIRCUIT_BREAKER_ATHENA_ENABLED=True,
        CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD=1,
    )
    try:
        client = AthenaClient()
        with patch.object(client, "_health_inner", side_effect=OSError("disk")):
            with pytest.raises(OSError):
                asyncio.run(client.health())
        snap = breaker.status()
        assert snap["state"] == CLOSED
        assert snap["failures_total"] == 0
    finally:
        breaker_mod.reset_registry()


def test_token_fetch_failure_is_covered_through_health(monkeypatch):
    """A flaky OAuth token endpoint surfaces as an httpx error inside
    `health()`; since the token fetch runs inside the breaker-wrapped
    call, it counts as Athena being unreachable."""
    breaker_mod.reset_registry()
    breaker = _force_breaker_with(
        monkeypatch,
        CIRCUIT_BREAKER_ATHENA_ENABLED=True,
        CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD=2,
    )
    try:
        client = AthenaClient()
        # Simulate the token-fetch path raising a transport error from
        # within the wrapped health() call.
        with patch.object(
            client,
            "_fetch_client_credentials_token",
            side_effect=httpx.ConnectError("token endpoint down"),
        ):
            for _ in range(2):
                with pytest.raises(httpx.ConnectError):
                    asyncio.run(client.health())
        assert breaker.status()["state"] == OPEN
    finally:
        breaker_mod.reset_registry()


def test_build_returns_idempotent_instance_per_settings_set():
    breaker_mod.reset_registry()
    a = build_athena_breaker()
    b = build_athena_breaker()
    assert a is b
    breaker_mod.reset_registry()
