"""
Phase 6 closeout contracts for outbound integration circuit breakers.

P6.1/P6.2/P6.3 each pinned one service. This file pins the portfolio
surface that ops tooling consumes across all three services:
default-off settings, cold-start metrics, /health/deps breaker blocks,
failure classification policy, CI wiring, and documentation coverage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import httpx
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.config import get_settings
from yuantus.integrations import circuit_breaker
from yuantus.integrations.athena import is_athena_breaker_failure
from yuantus.integrations.cad_ml import is_cad_ml_breaker_failure
from yuantus.integrations.dedup_vision import is_dedup_vision_breaker_failure
from yuantus.observability.metrics import render_runtime_prometheus_text


ROOT = Path(__file__).resolve().parents[4]

_BREAKERS: tuple[tuple[str, str, Callable[[Exception], bool]], ...] = (
    ("dedup_vision", "DEDUP_VISION", is_dedup_vision_breaker_failure),
    ("cad_ml", "CAD_ML", is_cad_ml_breaker_failure),
    ("athena", "ATHENA", is_athena_breaker_failure),
)

_SETTING_SUFFIX_DEFAULTS = {
    "ENABLED": False,
    "FAILURE_THRESHOLD": 5,
    "WINDOW_SECONDS": 60,
    "RECOVERY_SECONDS": 30,
    "HALF_OPEN_MAX_CALLS": 1,
    "BACKOFF_MAX_SECONDS": 600,
}

_METRIC_FAMILIES = (
    "yuantus_circuit_breaker_enabled",
    "yuantus_circuit_breaker_state",
    "yuantus_circuit_breaker_opens_total",
    "yuantus_circuit_breaker_short_circuited_total",
    "yuantus_circuit_breaker_failures_total",
    "yuantus_circuit_breaker_successes_total",
    "yuantus_circuit_breaker_failures_in_window",
)


def _status_error(code: int) -> httpx.HTTPStatusError:
    response = httpx.Response(
        status_code=code,
        request=httpx.Request("GET", "https://example.invalid/health"),
    )
    return httpx.HTTPStatusError(
        f"HTTP {code}",
        request=response.request,
        response=response,
    )


def test_phase6_breaker_settings_are_complete_uniform_and_default_off() -> None:
    fields = type(get_settings()).model_fields
    settings = get_settings()

    for _, setting_prefix, _ in _BREAKERS:
        for suffix, default in _SETTING_SUFFIX_DEFAULTS.items():
            key = f"CIRCUIT_BREAKER_{setting_prefix}_{suffix}"
            assert key in fields, f"missing Phase 6 setting: {key}"
            assert fields[key].default == default, (
                f"{key} default drifted from portfolio value {default!r}"
            )
            assert getattr(settings, key) == default, (
                f"{key} runtime default must remain default-off/uniform"
            )


def test_cold_start_metrics_expose_all_phase6_breakers() -> None:
    circuit_breaker.reset_registry()
    try:
        text = render_runtime_prometheus_text()
        for name, _, _ in _BREAKERS:
            assert f'name="{name}"' in text, (
                f"cold /api/v1/metrics scrape must expose breaker {name}"
            )
            assert f'yuantus_circuit_breaker_enabled{{name="{name}"}} 0' in text
            for state in ("closed", "open", "half_open"):
                assert (
                    f'yuantus_circuit_breaker_state{{name="{name}",state="{state}"}}'
                    in text
                ), f"missing state label {state!r} for {name}"

        for family in _METRIC_FAMILIES:
            assert family in text, f"missing metric family: {family}"
    finally:
        circuit_breaker.reset_registry()


def test_health_deps_exposes_all_phase6_breaker_blocks(monkeypatch) -> None:
    circuit_breaker.reset_registry()
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")
    try:
        app = create_app()
        response = TestClient(app).get("/api/v1/health/deps")
        assert response.status_code == 200
        external = response.json().get("external") or {}

        for name, _, _ in _BREAKERS:
            assert name in external, f"/health/deps missing external.{name}"
            breaker = external[name].get("breaker")
            assert breaker is not None, f"/health/deps missing {name}.breaker"
            assert breaker["name"] == name
            assert breaker["enabled"] is False
            assert breaker["state"] == "closed"
            for key in (
                "failures_in_window",
                "failure_threshold",
                "current_recovery_seconds",
                "opens_total",
                "short_circuited_total",
            ):
                assert key in breaker, f"{name}.breaker missing key {key}"
    finally:
        circuit_breaker.reset_registry()


def test_phase6_breakers_share_failure_classification_policy() -> None:
    counted = (
        httpx.ConnectError("network"),
        httpx.ReadTimeout("slow"),
        _status_error(500),
        _status_error(502),
        _status_error(503),
        _status_error(504),
        _status_error(408),
        _status_error(429),
        RuntimeError("unknown integration failure"),
    )
    not_counted = (
        _status_error(400),
        _status_error(401),
        _status_error(403),
        _status_error(404),
        _status_error(409),
        _status_error(422),
        FileNotFoundError("local secret missing"),
        PermissionError("local secret denied"),
        OSError("local file problem"),
    )

    for name, _, predicate in _BREAKERS:
        for exc in counted:
            assert predicate(exc), f"{name} must count {exc!r}"
        for exc in not_counted:
            assert not predicate(exc), f"{name} must not count {exc!r}"


def test_phase6_closeout_docs_and_runbook_cover_all_breakers() -> None:
    closeout_path = ROOT / "docs/DEV_AND_VERIFICATION_PHASE6_CIRCUIT_BREAKER_CLOSEOUT_20260510.md"
    closeout = closeout_path.read_text(encoding="utf-8")
    runbook = (ROOT / "docs/RUNBOOK_JOBS_DIAG.md").read_text(encoding="utf-8")
    index = (ROOT / "docs/DELIVERY_DOC_INDEX.md").read_text(encoding="utf-8")

    assert str(closeout_path.relative_to(ROOT)) in index

    for name, setting_prefix, _ in _BREAKERS:
        assert name in closeout
        assert f"CIRCUIT_BREAKER_{setting_prefix}_ENABLED" in closeout
        assert f"YUANTUS_CIRCUIT_BREAKER_{setting_prefix}_ENABLED" in runbook

    for doc_name in (
        "DEV_AND_VERIFICATION_CIRCUIT_BREAKER_DEDUP_VISION_20260507.md",
        "DEV_AND_VERIFICATION_CIRCUIT_BREAKER_CAD_ML_20260508.md",
        "DEV_AND_VERIFICATION_CIRCUIT_BREAKER_ATHENA_20260510.md",
    ):
        assert doc_name in closeout, f"closeout missing source PR doc {doc_name}"


def test_phase6_closeout_contract_is_registered_in_ci_contract_job() -> None:
    ci_yml = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert (
        "src/yuantus/meta_engine/tests/"
        "test_phase6_circuit_breaker_closeout_contracts.py"
    ) in ci_yml
