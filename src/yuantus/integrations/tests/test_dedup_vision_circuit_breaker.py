from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx
import pytest

from yuantus.integrations import circuit_breaker as breaker_mod
from yuantus.integrations.circuit_breaker import (
    CLOSED,
    OPEN,
    CircuitOpenError,
)
from yuantus.integrations.dedup_vision import (
    DEDUP_VISION_BREAKER_NAME,
    DedupVisionClient,
    build_dedup_vision_breaker,
)


def _force_breaker_with(**overrides):
    """Replace the registered dedup_vision breaker with one built from overridden settings."""
    from yuantus.config import get_settings

    breaker_mod.reset_registry()
    settings = get_settings()
    saved = {}
    fields = {
        "CIRCUIT_BREAKER_DEDUP_VISION_ENABLED",
        "CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD",
        "CIRCUIT_BREAKER_DEDUP_VISION_WINDOW_SECONDS",
        "CIRCUIT_BREAKER_DEDUP_VISION_RECOVERY_SECONDS",
        "CIRCUIT_BREAKER_DEDUP_VISION_HALF_OPEN_MAX_CALLS",
        "CIRCUIT_BREAKER_DEDUP_VISION_BACKOFF_MAX_SECONDS",
    }
    for field in fields:
        saved[field] = getattr(settings, field)
    try:
        for key, value in overrides.items():
            setattr(settings, key, value)
        return build_dedup_vision_breaker(), saved
    except Exception:  # pragma: no cover
        for field, value in saved.items():
            setattr(settings, field, value)
        raise


def _restore_settings(saved):
    from yuantus.config import get_settings

    settings = get_settings()
    for field, value in saved.items():
        setattr(settings, field, value)


def test_default_off_is_passthrough():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=False)
    try:
        assert breaker.enabled is False
        client = DedupVisionClient()
        # Force inner method to raise; with breaker disabled, raw error must surface.
        with patch.object(
            client, "_health_inner", side_effect=httpx.ConnectError("boom")
        ):
            with pytest.raises(httpx.ConnectError):
                asyncio.run(client.health())
        # Disabled breaker records nothing.
        snapshot = breaker.status()
        assert snapshot["state"] == CLOSED
        assert snapshot["failures_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_enabled_breaker_opens_after_repeated_failures():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=3,
        CIRCUIT_BREAKER_DEDUP_VISION_RECOVERY_SECONDS=5,
        CIRCUIT_BREAKER_DEDUP_VISION_HALF_OPEN_MAX_CALLS=1,
    )
    try:
        client = DedupVisionClient()
        with patch.object(
            client, "_health_inner", side_effect=httpx.ConnectError("upstream")
        ):
            for _ in range(3):
                with pytest.raises(httpx.ConnectError):
                    asyncio.run(client.health())
        assert breaker.status()["state"] == OPEN
        # Subsequent call short-circuits via CircuitOpenError instead of httpx.ConnectError.
        with patch.object(
            client, "_health_inner", side_effect=AssertionError("must not be called")
        ):
            with pytest.raises(CircuitOpenError):
                asyncio.run(client.health())
        assert breaker.status()["short_circuited_total"] == 1
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_breaker_name_is_stable():
    assert DEDUP_VISION_BREAKER_NAME == "dedup_vision"


def test_sync_paths_use_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=2,
    )
    try:
        client = DedupVisionClient()
        with patch.object(
            client,
            "_index_add_sync_inner",
            side_effect=httpx.ConnectError("upstream"),
        ):
            for _ in range(2):
                with pytest.raises(httpx.ConnectError):
                    client.index_add_sync(
                        file_path="/tmp/missing.dwg", user_name="u"
                    )
        assert breaker.status()["state"] == OPEN
        with pytest.raises(CircuitOpenError):
            client.index_add_sync(file_path="/tmp/missing.dwg", user_name="u")
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_build_returns_idempotent_instance_per_settings_set():
    breaker_mod.reset_registry()
    a = build_dedup_vision_breaker()
    b = build_dedup_vision_breaker()
    assert a is b
    breaker_mod.reset_registry()


# ---------------------------------------------------------------------------
# Phase 6 P6.1 — failure classification: 4xx must not trip the breaker.
# ---------------------------------------------------------------------------


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build an HTTPStatusError with a real Response carrying the given status."""
    response = httpx.Response(status_code=status_code, request=httpx.Request("GET", "http://x"))
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=response.request, response=response
    )


def test_4xx_client_errors_do_not_trip_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=2,
    )
    try:
        client = DedupVisionClient()
        for status in (400, 401, 403, 404, 422):
            err = _http_status_error(status)
            with patch.object(client, "_search_sync_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    client.search_sync(file_path="/tmp/x.dwg")
        snap = breaker.status()
        assert snap["state"] == CLOSED, (
            f"4xx must not implicate the breaker; state={snap['state']}"
        )
        assert snap["failures_total"] == 0
        assert snap["opens_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_5xx_server_errors_trip_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=3,
    )
    try:
        client = DedupVisionClient()
        for status in (500, 502, 503):
            err = _http_status_error(status)
            with patch.object(client, "_search_sync_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    client.search_sync(file_path="/tmp/x.dwg")
        assert breaker.status()["state"] == OPEN
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_408_and_429_are_counted_as_breaker_failures():
    """408 (timeout) and 429 (too many requests) are recoverable upstream
    pressure signals — count them so the breaker can shed load."""
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=2,
    )
    try:
        client = DedupVisionClient()
        for status in (408, 429):
            err = _http_status_error(status)
            with patch.object(client, "_search_sync_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    client.search_sync(file_path="/tmp/x.dwg")
        assert breaker.status()["state"] == OPEN
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_request_error_trips_breaker():
    """Network-layer failures (RequestError subclasses) always count."""
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=2,
    )
    try:
        client = DedupVisionClient()
        with patch.object(
            client, "_health_inner", side_effect=httpx.ConnectError("net")
        ):
            for _ in range(2):
                with pytest.raises(httpx.ConnectError):
                    asyncio.run(client.health())
        assert breaker.status()["state"] == OPEN
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


# ---------------------------------------------------------------------------
# Local I/O errors must not implicate the breaker (regression for review
# finding: a caller passing a non-existent file would otherwise trip the
# breaker on every attempt and short-circuit healthy upstream traffic).
# ---------------------------------------------------------------------------


def test_search_sync_missing_file_does_not_open_breaker():
    """A bad caller path (no file at file_path) raises FileNotFoundError
    before any network call. That is local-side, not upstream — must not
    count toward the breaker's failure window."""
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=2,
    )
    try:
        client = DedupVisionClient()
        for _ in range(5):
            with pytest.raises(FileNotFoundError):
                client.search_sync(file_path="/nonexistent/dir/missing.dwg")
        snap = breaker.status()
        assert snap["state"] == CLOSED, (
            f"FileNotFoundError must not implicate the breaker; got state={snap['state']}"
        )
        assert snap["failures_total"] == 0
        assert snap["opens_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_index_add_sync_missing_file_does_not_open_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=2,
    )
    try:
        client = DedupVisionClient()
        for _ in range(5):
            with pytest.raises(FileNotFoundError):
                client.index_add_sync(
                    file_path="/nonexistent/dir/missing.dwg", user_name="u"
                )
        snap = breaker.status()
        assert snap["state"] == CLOSED
        assert snap["failures_total"] == 0
        assert snap["opens_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_permission_error_does_not_open_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_DEDUP_VISION_ENABLED=True,
        CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD=1,
    )
    try:
        client = DedupVisionClient()
        with patch.object(
            client,
            "_search_sync_inner",
            side_effect=PermissionError("denied"),
        ):
            with pytest.raises(PermissionError):
                client.search_sync(file_path="/tmp/x.dwg")
        snap = breaker.status()
        assert snap["state"] == CLOSED
        assert snap["failures_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()
