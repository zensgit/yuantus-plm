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
from yuantus.integrations.cad_ml import (
    CAD_ML_BREAKER_NAME,
    CadMLClient,
    build_cad_ml_breaker,
)


def _force_breaker_with(**overrides):
    """Replace the registered cad_ml breaker with one built from overridden settings."""
    from yuantus.config import get_settings

    breaker_mod.reset_registry()
    settings = get_settings()
    saved = {}
    fields = {
        "CIRCUIT_BREAKER_CAD_ML_ENABLED",
        "CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD",
        "CIRCUIT_BREAKER_CAD_ML_WINDOW_SECONDS",
        "CIRCUIT_BREAKER_CAD_ML_RECOVERY_SECONDS",
        "CIRCUIT_BREAKER_CAD_ML_HALF_OPEN_MAX_CALLS",
        "CIRCUIT_BREAKER_CAD_ML_BACKOFF_MAX_SECONDS",
    }
    for field in fields:
        saved[field] = getattr(settings, field)
    try:
        for key, value in overrides.items():
            setattr(settings, key, value)
        return build_cad_ml_breaker(), saved
    except Exception:  # pragma: no cover
        for field, value in saved.items():
            setattr(settings, field, value)
        raise


def _restore_settings(saved):
    from yuantus.config import get_settings

    settings = get_settings()
    for field, value in saved.items():
        setattr(settings, field, value)


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    response = httpx.Response(
        status_code=status_code, request=httpx.Request("GET", "http://x")
    )
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=response.request, response=response
    )


def test_breaker_name_is_stable():
    assert CAD_ML_BREAKER_NAME == "cad_ml"


def test_default_off_is_passthrough():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(CIRCUIT_BREAKER_CAD_ML_ENABLED=False)
    try:
        assert breaker.enabled is False
        client = CadMLClient()
        with patch.object(
            client, "_health_inner", side_effect=httpx.ConnectError("boom")
        ):
            with pytest.raises(httpx.ConnectError):
                asyncio.run(client.health())
        snapshot = breaker.status()
        assert snapshot["state"] == CLOSED
        assert snapshot["failures_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_enabled_breaker_opens_after_repeated_request_errors():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_CAD_ML_ENABLED=True,
        CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD=3,
    )
    try:
        client = CadMLClient()
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
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_sync_paths_share_breaker():
    """All three sync methods must route through the same breaker — a
    failure on `vision_analyze_sync` must contribute to the same counter
    that `render_cad_preview_sync` checks."""
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_CAD_ML_ENABLED=True,
        CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD=2,
    )
    try:
        client = CadMLClient()
        # Failure 1 via vision_analyze.
        with patch.object(
            client, "_vision_analyze_sync_inner", side_effect=httpx.ConnectError("x")
        ):
            with pytest.raises(httpx.ConnectError):
                client.vision_analyze_sync(image_base64="ZGF0YQ==")
        # Failure 2 via render_cad_preview — should trip after this one.
        with patch.object(
            client, "_render_cad_preview_sync_inner", side_effect=httpx.ConnectError("x")
        ):
            with pytest.raises(httpx.ConnectError):
                client.render_cad_preview_sync(file_path="/tmp/x.dwg")
        assert breaker.status()["state"] == OPEN
        # Subsequent ocr_extract is short-circuited.
        with pytest.raises(CircuitOpenError):
            client.ocr_extract_sync(file_path="/tmp/x.dwg")
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_4xx_client_errors_do_not_trip_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_CAD_ML_ENABLED=True,
        CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD=2,
    )
    try:
        client = CadMLClient()
        for status in (400, 401, 403, 404, 422):
            err = _http_status_error(status)
            with patch.object(client, "_vision_analyze_sync_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    client.vision_analyze_sync(image_base64="ZGF0YQ==")
        snap = breaker.status()
        assert snap["state"] == CLOSED
        assert snap["failures_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_5xx_server_errors_trip_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_CAD_ML_ENABLED=True,
        CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD=3,
    )
    try:
        client = CadMLClient()
        for status in (500, 502, 503):
            err = _http_status_error(status)
            with patch.object(client, "_vision_analyze_sync_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    client.vision_analyze_sync(image_base64="ZGF0YQ==")
        assert breaker.status()["state"] == OPEN
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_408_and_429_are_counted_as_breaker_failures():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_CAD_ML_ENABLED=True,
        CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD=2,
    )
    try:
        client = CadMLClient()
        for status in (408, 429):
            err = _http_status_error(status)
            with patch.object(client, "_vision_analyze_sync_inner", side_effect=err):
                with pytest.raises(httpx.HTTPStatusError):
                    client.vision_analyze_sync(image_base64="ZGF0YQ==")
        assert breaker.status()["state"] == OPEN
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_ocr_extract_missing_file_does_not_open_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_CAD_ML_ENABLED=True,
        CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD=2,
    )
    try:
        client = CadMLClient()
        for _ in range(5):
            with pytest.raises(FileNotFoundError):
                client.ocr_extract_sync(file_path="/nonexistent/dir/missing.dwg")
        snap = breaker.status()
        assert snap["state"] == CLOSED
        assert snap["failures_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_render_cad_preview_missing_file_does_not_open_breaker():
    breaker_mod.reset_registry()
    breaker, saved = _force_breaker_with(
        CIRCUIT_BREAKER_CAD_ML_ENABLED=True,
        CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD=2,
    )
    try:
        client = CadMLClient()
        for _ in range(5):
            with pytest.raises(FileNotFoundError):
                client.render_cad_preview_sync(file_path="/nonexistent/dir/missing.dwg")
        snap = breaker.status()
        assert snap["state"] == CLOSED
        assert snap["failures_total"] == 0
    finally:
        _restore_settings(saved)
        breaker_mod.reset_registry()


def test_build_returns_idempotent_instance_per_settings_set():
    breaker_mod.reset_registry()
    a = build_cad_ml_breaker()
    b = build_cad_ml_breaker()
    assert a is b
    breaker_mod.reset_registry()
