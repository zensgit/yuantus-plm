from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "docker-compose.yml").is_file():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError(
        "Could not locate repo root (expected pyproject.toml + docker-compose.yml)"
    )


def _env_to_dict(env: Any) -> dict[str, str]:
    if env is None:
        return {}
    if isinstance(env, dict):
        return {str(k): str(v) for k, v in env.items()}
    if isinstance(env, list):
        out: dict[str, str] = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                key, value = item.split("=", 1)
                out[key] = value
        return out
    raise AssertionError(f"Unexpected environment type: {type(env)}")


def _as_str_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str):
        return [val]
    raise AssertionError(f"Unexpected list-like type: {type(val)}")


def _load_compose() -> dict[str, Any]:
    repo_root = _find_repo_root(Path(__file__))
    compose_yml = repo_root / "docker-compose.yml"
    assert compose_yml.is_file(), f"Missing {compose_yml}"
    return yaml.safe_load(compose_yml.read_text(encoding="utf-8")) or {}


def test_scheduler_compose_service_is_opt_in_and_default_disabled() -> None:
    doc = _load_compose()
    services = doc.get("services") or {}
    scheduler = services.get("scheduler") or {}

    assert scheduler, "docker-compose.yml must define an opt-in scheduler service."
    assert _as_str_list(scheduler.get("profiles")) == ["scheduler"], (
        "scheduler compose service must be hidden behind the scheduler profile so "
        "plain docker compose up api worker remains unchanged."
    )

    env = _env_to_dict(scheduler.get("environment"))
    assert env.get("YUANTUS_SCHEDULER_ENABLED") == "${YUANTUS_SCHEDULER_ENABLED:-false}", (
        "scheduler compose service must default to disabled even when the profile is selected."
    )
    assert "restart" not in scheduler, (
        "scheduler service should not restart-loop when profile is selected but "
        "YUANTUS_SCHEDULER_ENABLED is left false."
    )


def test_scheduler_compose_service_uses_worker_image_and_safe_command() -> None:
    doc = _load_compose()
    scheduler = (doc.get("services") or {}).get("scheduler") or {}
    build = scheduler.get("build") or {}
    command = _as_str_list(scheduler.get("command"))

    assert build.get("dockerfile") == "Dockerfile.worker", (
        "scheduler should reuse the worker runtime image instead of the API server image."
    )
    assert command[:2] == ["yuantus", "scheduler"], (
        "scheduler service must run the scheduler CLI directly."
        f"\nGot: {command}"
    )
    assert "--force" not in command, (
        "compose scheduler service must not bypass SCHEDULER_ENABLED with --force."
    )
    assert "--poll-interval" in command
    assert "${YUANTUS_SCHEDULER_POLL_INTERVAL_SECONDS:-60}" in command
    assert "--tenant" in command
    assert "${YUANTUS_SCHEDULER_TENANT_ID:-tenant-1}" in command
    assert "--org" in command
    assert "${YUANTUS_SCHEDULER_ORG_ID:-org-1}" in command


def test_scheduler_compose_service_waits_for_api_and_exposes_task_toggles() -> None:
    doc = _load_compose()
    scheduler = (doc.get("services") or {}).get("scheduler") or {}
    depends_on = scheduler.get("depends_on") or {}
    env = _env_to_dict(scheduler.get("environment"))

    assert (depends_on.get("api") or {}).get("condition") == "service_healthy", (
        "scheduler should start only after the API service has run migrations and is healthy."
    )
    for key, expected in {
        "YUANTUS_DATABASE_URL": "postgres:5432",
        "YUANTUS_SCHEMA_MODE": "migrations",
        "YUANTUS_TENANCY_MODE": "${YUANTUS_TENANCY_MODE:-single}",
        "YUANTUS_SCHEDULER_SYSTEM_USER_ID": "${YUANTUS_SCHEDULER_SYSTEM_USER_ID:-1}",
        "YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED": "${YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED:-true}",
        "YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED": "${YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED:-true}",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_ENABLED": "${YUANTUS_SCHEDULER_BOM_TO_MBOM_ENABLED:-false}",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_INTERVAL_SECONDS": "${YUANTUS_SCHEDULER_BOM_TO_MBOM_INTERVAL_SECONDS:-3600}",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_PRIORITY": "${YUANTUS_SCHEDULER_BOM_TO_MBOM_PRIORITY:-85}",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_MAX_ATTEMPTS": "${YUANTUS_SCHEDULER_BOM_TO_MBOM_MAX_ATTEMPTS:-1}",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_SOURCE_ITEM_IDS": "${YUANTUS_SCHEDULER_BOM_TO_MBOM_SOURCE_ITEM_IDS:-}",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_PLANT_CODE": "${YUANTUS_SCHEDULER_BOM_TO_MBOM_PLANT_CODE:-}",
    }.items():
        value = env.get(key)
        assert value is not None, f"scheduler compose service missing environment {key}"
        assert expected in value, f"{key} should contain {expected!r}; got {value!r}"


def test_scheduler_compose_service_delivery_doc_is_indexed() -> None:
    repo_root = _find_repo_root(Path(__file__))
    doc = repo_root / "docs" / "DEV_AND_VERIFICATION_SCHEDULER_COMPOSE_SERVICE_20260421.md"
    index = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"

    assert doc.is_file(), f"Missing delivery doc: {doc}"
    index_text = index.read_text(encoding="utf-8")
    assert doc.relative_to(repo_root).as_posix() in index_text

    doc_text = doc.read_text(encoding="utf-8")
    for token in (
        "profiles: [\"scheduler\"]",
        "YUANTUS_SCHEDULER_ENABLED=false",
        "docker compose --profile scheduler up -d scheduler",
        "does not run first-run bootstrap",
    ):
        assert token in doc_text
