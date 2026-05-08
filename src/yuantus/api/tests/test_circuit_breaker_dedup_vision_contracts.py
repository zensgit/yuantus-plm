"""
Phase 6 P6.1 — DedupCAD Vision circuit breaker closeout contracts.

These contracts pin the *downstream-consumer* surface (settings keys, metric
families, label cardinality, health-deps shape) that future P6.2/P6.3 PRs +
ops tooling depend on. They are intentionally regression-prevention only —
behavioural tests live in `src/yuantus/integrations/tests/`.

Pinning rules:
- Settings field names must not change without a contract bump.
- Metric prefix `yuantus_circuit_breaker_*` is stable; renaming requires
  Prometheus dashboard migration.
- Default-off feature flag is the project-wide invariant; production
  enablement is per-deployment.
- `/health/deps` exposes a `breaker` block under integrations that have a
  registered breaker, regardless of `HEALTHCHECK_EXTERNAL`.
"""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.integrations import circuit_breaker
from yuantus.integrations.dedup_vision import (
    DEDUP_VISION_BREAKER_NAME,
    build_dedup_vision_breaker,
    is_dedup_vision_breaker_failure,
)
from yuantus.observability.metrics import (
    render_circuit_breaker_metrics,
    render_runtime_prometheus_text,
)


# ---------------------------------------------------------------------------
# Contract 1: settings keys + default values are pinned.
# ---------------------------------------------------------------------------

_PINNED_SETTING_DEFAULTS = {
    "CIRCUIT_BREAKER_DEDUP_VISION_ENABLED": False,
    "CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD": 5,
    "CIRCUIT_BREAKER_DEDUP_VISION_WINDOW_SECONDS": 60,
    "CIRCUIT_BREAKER_DEDUP_VISION_RECOVERY_SECONDS": 30,
    "CIRCUIT_BREAKER_DEDUP_VISION_HALF_OPEN_MAX_CALLS": 1,
    "CIRCUIT_BREAKER_DEDUP_VISION_BACKOFF_MAX_SECONDS": 600,
}


def test_circuit_breaker_settings_keys_and_defaults_are_pinned() -> None:
    settings_cls = type(get_settings())
    fields = settings_cls.model_fields
    for key, default in _PINNED_SETTING_DEFAULTS.items():
        assert key in fields, f"missing pinned setting: {key}"
        assert fields[key].default == default, (
            f"{key} default {fields[key].default!r} != pinned {default!r}; "
            "default-off contract violated or threshold drift"
        )


def test_default_breaker_is_disabled() -> None:
    """Project-wide invariant: production enablement is per-deployment."""
    settings = get_settings()
    assert settings.CIRCUIT_BREAKER_DEDUP_VISION_ENABLED is False


# ---------------------------------------------------------------------------
# Contract 2: metric families + label cardinality.
# ---------------------------------------------------------------------------

_PINNED_METRIC_FAMILIES = (
    "yuantus_circuit_breaker_enabled",
    "yuantus_circuit_breaker_state",
    "yuantus_circuit_breaker_opens_total",
    "yuantus_circuit_breaker_short_circuited_total",
    "yuantus_circuit_breaker_failures_total",
    "yuantus_circuit_breaker_successes_total",
    "yuantus_circuit_breaker_failures_in_window",
)
_PINNED_STATE_LABELS = ("closed", "open", "half_open")


def test_metric_families_and_labels_are_pinned() -> None:
    circuit_breaker.reset_registry()
    try:
        build_dedup_vision_breaker()
        statuses = [b.status() for b in circuit_breaker.list_breakers().values()]
        text = render_circuit_breaker_metrics(statuses)
        for family in _PINNED_METRIC_FAMILIES:
            assert family in text, f"metric family missing: {family}"
        for state in _PINNED_STATE_LABELS:
            assert (
                f'state="{state}"' in text
            ), f"pinned state label missing: {state}"
        # Cardinality guard: every state line names the breaker exactly once
        # to keep label set finite.
        state_lines = [
            line
            for line in text.splitlines()
            if line.startswith("yuantus_circuit_breaker_state{")
        ]
        for line in state_lines:
            assert line.count(f'name="{DEDUP_VISION_BREAKER_NAME}"') == 1, line
    finally:
        circuit_breaker.reset_registry()


def test_runtime_prometheus_includes_circuit_breaker_section_when_registered() -> None:
    circuit_breaker.reset_registry()
    try:
        build_dedup_vision_breaker()
        text = render_runtime_prometheus_text()
        assert "yuantus_circuit_breaker_enabled" in text
        assert f'name="{DEDUP_VISION_BREAKER_NAME}"' in text
    finally:
        circuit_breaker.reset_registry()


def test_cold_start_metrics_include_dedup_vision_breaker() -> None:
    """Critical contract: Prometheus scrape that hits /api/v1/metrics before
    any DedupVisionClient call or /health/deps probe must still emit the
    yuantus_circuit_breaker_* families. `render_runtime_prometheus_text`
    pre-registers the dedup_vision breaker for exactly this case so the
    metrics families do not silently disappear depending on scrape order.
    """
    circuit_breaker.reset_registry()
    try:
        text = render_runtime_prometheus_text()
        # No prior call, no client constructed — but the metrics endpoint
        # must still emit the dedup_vision breaker section.
        assert "yuantus_circuit_breaker_enabled" in text
        assert f'name="{DEDUP_VISION_BREAKER_NAME}"' in text
        assert (
            f'yuantus_circuit_breaker_state{{name="{DEDUP_VISION_BREAKER_NAME}",'
            'state="closed"}}'.replace("}}", "}") in text
        )
    finally:
        circuit_breaker.reset_registry()


# ---------------------------------------------------------------------------
# Contract 3: /health/deps surfaces breaker state for dedup_vision.
# ---------------------------------------------------------------------------


def test_health_deps_surfaces_dedup_vision_breaker_block() -> None:
    circuit_breaker.reset_registry()
    settings = get_settings()
    original_auth = settings.AUTH_MODE
    settings.AUTH_MODE = "optional"
    try:
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/v1/health/deps")
        assert response.status_code == 200
        body = response.json()
        external = body.get("external") or {}
        assert "dedup_vision" in external
        breaker_block = external["dedup_vision"].get("breaker")
        assert breaker_block is not None, (
            "Phase 6 P6.1 contract: /health/deps must expose breaker info "
            "for dedup_vision so ops can verify state without scraping metrics"
        )
        # Pinned subset of breaker status keys consumed by ops dashboards.
        for key in ("name", "enabled", "state", "opens_total"):
            assert key in breaker_block, f"breaker status missing key: {key}"
        assert breaker_block["name"] == DEDUP_VISION_BREAKER_NAME
        assert isinstance(breaker_block["enabled"], bool)
    finally:
        settings.AUTH_MODE = original_auth
        circuit_breaker.reset_registry()


# ---------------------------------------------------------------------------
# Contract 3b: failure classification policy is pinned (4xx must not trip).
# ---------------------------------------------------------------------------


import httpx as _httpx_for_classification  # local alias to avoid collisions


def _stub_status_error(code: int) -> _httpx_for_classification.HTTPStatusError:
    response = _httpx_for_classification.Response(
        status_code=code,
        request=_httpx_for_classification.Request("GET", "http://x"),
    )
    return _httpx_for_classification.HTTPStatusError(
        f"HTTP {code}", request=response.request, response=response
    )


def test_failure_classification_pins_breaker_policy() -> None:
    """Phase 6 P6.1 contract: only service-side / recoverable failures
    implicate the breaker. Other 4xx are caller-side errors and must
    not trip protection meant for upstream outages."""
    counted = (
        _httpx_for_classification.ConnectError("net"),
        _httpx_for_classification.ReadTimeout("slow"),
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
    )
    for exc in counted:
        assert is_dedup_vision_breaker_failure(exc), (
            f"{exc!r} must count toward the breaker's failure window"
        )
    for exc in not_counted:
        assert not is_dedup_vision_breaker_failure(exc), (
            f"{exc!r} is a client-side error and must not trip the breaker"
        )


# ---------------------------------------------------------------------------
# Contract 4: metric output is Prometheus parseable (well-formed lines).
# ---------------------------------------------------------------------------

_LINE_PATTERN = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+-?\d+(\.\d+)?$")


def test_circuit_breaker_metric_lines_are_well_formed() -> None:
    circuit_breaker.reset_registry()
    try:
        build_dedup_vision_breaker()
        text = render_circuit_breaker_metrics(
            [b.status() for b in circuit_breaker.list_breakers().values()]
        )
        for line in text.splitlines():
            if not line or line.startswith("#"):
                continue
            assert _LINE_PATTERN.match(line), f"malformed metric line: {line!r}"
    finally:
        circuit_breaker.reset_registry()
