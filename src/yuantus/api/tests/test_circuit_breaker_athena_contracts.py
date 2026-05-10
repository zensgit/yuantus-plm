"""
Phase 6 P6.3 — Athena ECM circuit breaker closeout contracts.

Mirrors P6.1/P6.2 contract structure. Pins settings, default-off
invariant, metric families, cold-start metric visibility, /health/deps
shape, and the failure-classification policy.
"""
from __future__ import annotations

import re

import httpx
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.integrations import circuit_breaker
from yuantus.integrations.athena import (
    ATHENA_BREAKER_NAME,
    build_athena_breaker,
    is_athena_breaker_failure,
)
from yuantus.observability.metrics import (
    render_circuit_breaker_metrics,
    render_runtime_prometheus_text,
)


_PINNED_SETTING_DEFAULTS = {
    "CIRCUIT_BREAKER_ATHENA_ENABLED": False,
    "CIRCUIT_BREAKER_ATHENA_FAILURE_THRESHOLD": 5,
    "CIRCUIT_BREAKER_ATHENA_WINDOW_SECONDS": 60,
    "CIRCUIT_BREAKER_ATHENA_RECOVERY_SECONDS": 30,
    "CIRCUIT_BREAKER_ATHENA_HALF_OPEN_MAX_CALLS": 1,
    "CIRCUIT_BREAKER_ATHENA_BACKOFF_MAX_SECONDS": 600,
}


def test_circuit_breaker_settings_keys_and_defaults_are_pinned() -> None:
    fields = type(get_settings()).model_fields
    for key, default in _PINNED_SETTING_DEFAULTS.items():
        assert key in fields, f"missing pinned setting: {key}"
        assert fields[key].default == default, (
            f"{key} default {fields[key].default!r} != pinned {default!r}"
        )


def test_default_breaker_is_disabled() -> None:
    assert get_settings().CIRCUIT_BREAKER_ATHENA_ENABLED is False


_PINNED_METRIC_FAMILIES = (
    "yuantus_circuit_breaker_enabled",
    "yuantus_circuit_breaker_state",
    "yuantus_circuit_breaker_opens_total",
    "yuantus_circuit_breaker_short_circuited_total",
    "yuantus_circuit_breaker_failures_total",
    "yuantus_circuit_breaker_successes_total",
    "yuantus_circuit_breaker_failures_in_window",
)


def test_metric_families_emitted_for_athena_breaker() -> None:
    circuit_breaker.reset_registry()
    try:
        build_athena_breaker()
        statuses = [b.status() for b in circuit_breaker.list_breakers().values()]
        text = render_circuit_breaker_metrics(statuses)
        for family in _PINNED_METRIC_FAMILIES:
            assert family in text, f"metric family missing: {family}"
        assert f'name="{ATHENA_BREAKER_NAME}"' in text
    finally:
        circuit_breaker.reset_registry()


def test_cold_start_metrics_include_athena_breaker() -> None:
    """A Prometheus scrape arriving before any AthenaClient call must
    still emit the athena breaker metrics — depends on
    `render_runtime_prometheus_text` pre-registering it."""
    circuit_breaker.reset_registry()
    try:
        text = render_runtime_prometheus_text()
        assert f'name="{ATHENA_BREAKER_NAME}"' in text
        assert (
            f'yuantus_circuit_breaker_state{{name="{ATHENA_BREAKER_NAME}",state="closed"}}'
            in text
        )
    finally:
        circuit_breaker.reset_registry()


def test_all_three_breakers_pre_registered_on_cold_scrape() -> None:
    """Phase 6 invariant: a cold /api/v1/metrics scrape exposes all three
    breakers (dedup_vision, cad_ml, athena) — P6.4 will harden this into
    a portfolio contract, but pin the minimum here so a regression in any
    one pre-registration call is caught immediately."""
    circuit_breaker.reset_registry()
    try:
        text = render_runtime_prometheus_text()
        for name in ("dedup_vision", "cad_ml", "athena"):
            assert f'name="{name}"' in text, f"breaker {name} missing from cold scrape"
    finally:
        circuit_breaker.reset_registry()


def test_health_deps_surfaces_athena_breaker_block(monkeypatch) -> None:
    circuit_breaker.reset_registry()
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")
    try:
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/health/deps")
        assert response.status_code == 200
        external = (response.json().get("external") or {})
        assert "athena" in external
        breaker_block = external["athena"].get("breaker")
        assert breaker_block is not None, (
            "P6.3 contract: /health/deps must expose breaker info for athena"
        )
        for key in ("name", "enabled", "state", "opens_total"):
            assert key in breaker_block, f"breaker status missing key: {key}"
        assert breaker_block["name"] == ATHENA_BREAKER_NAME
        assert isinstance(breaker_block["enabled"], bool)
    finally:
        circuit_breaker.reset_registry()


def _stub_status_error(code: int) -> httpx.HTTPStatusError:
    response = httpx.Response(
        status_code=code, request=httpx.Request("GET", "http://x")
    )
    return httpx.HTTPStatusError(
        f"HTTP {code}", request=response.request, response=response
    )


def test_failure_classification_pins_breaker_policy() -> None:
    counted = (
        httpx.ConnectError("net"),
        httpx.ReadTimeout("slow"),
        _stub_status_error(500),
        _stub_status_error(502),
        _stub_status_error(503),
        _stub_status_error(504),
        _stub_status_error(408),
        _stub_status_error(429),
    )
    not_counted = (
        _stub_status_error(400),
        _stub_status_error(401),
        _stub_status_error(403),
        _stub_status_error(404),
        _stub_status_error(409),
        _stub_status_error(422),
        FileNotFoundError("missing"),
        PermissionError("denied"),
        OSError("disk full"),
    )
    for exc in counted:
        assert is_athena_breaker_failure(exc), f"{exc!r} must count"
    for exc in not_counted:
        assert not is_athena_breaker_failure(exc), f"{exc!r} must NOT count"


_LINE_PATTERN = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+-?\d+(\.\d+)?$")


def test_circuit_breaker_metric_lines_are_well_formed() -> None:
    circuit_breaker.reset_registry()
    try:
        build_athena_breaker()
        text = render_circuit_breaker_metrics(
            [b.status() for b in circuit_breaker.list_breakers().values()]
        )
        for line in text.splitlines():
            if not line or line.startswith("#"):
                continue
            assert _LINE_PATTERN.match(line), f"malformed metric line: {line!r}"
    finally:
        circuit_breaker.reset_registry()
