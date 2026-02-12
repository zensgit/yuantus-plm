from __future__ import annotations

import subprocess

from typer.testing import CliRunner

from yuantus.cli import app
from yuantus.config.settings import get_settings

runner = CliRunner()


class _Completed:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_db_command_rejects_conflicting_identity_flags() -> None:
    result = runner.invoke(
        app,
        [
            "db",
            "upgrade",
            "--db-url",
            "sqlite:///./meta.db",
            "--identity",
        ],
    )
    assert result.exit_code == 1
    assert "--db-url and --identity are mutually exclusive" in result.output


def test_db_upgrade_identity_uses_identity_database_url(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, cwd=None, env=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["env"] = env
        return _Completed(returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    get_settings.cache_clear()
    try:
        result = runner.invoke(
            app,
            ["db", "upgrade", "--identity"],
            env={
                "YUANTUS_DATABASE_URL": "sqlite:///./meta-default.db",
                "YUANTUS_IDENTITY_DATABASE_URL": "sqlite:///./identity-only.db",
            },
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0, result.output
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["YUANTUS_DATABASE_URL"] == "sqlite:///./identity-only.db"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[-2:] == ["upgrade", "head"]


def test_db_upgrade_identity_falls_back_to_primary_database_url(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, cwd=None, env=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["env"] = env
        return _Completed(returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    get_settings.cache_clear()
    try:
        result = runner.invoke(
            app,
            ["db", "upgrade", "--identity"],
            env={
                "YUANTUS_DATABASE_URL": "sqlite:///./meta-fallback.db",
                "YUANTUS_IDENTITY_DATABASE_URL": "",
            },
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0, result.output
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["YUANTUS_DATABASE_URL"] == "sqlite:///./meta-fallback.db"


def test_db_upgrade_with_db_url_override_sets_alembic_target_url(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(cmd, cwd=None, env=None):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["env"] = env
        return _Completed(returncode=0)

    monkeypatch.setattr(subprocess, "run", _fake_run)
    get_settings.cache_clear()
    try:
        result = runner.invoke(
            app,
            ["db", "upgrade", "--db-url", "sqlite:///./override.db"],
            env={
                "YUANTUS_DATABASE_URL": "sqlite:///./meta-default.db",
                "YUANTUS_IDENTITY_DATABASE_URL": "sqlite:///./identity-default.db",
            },
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0, result.output
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["YUANTUS_DATABASE_URL"] == "sqlite:///./override.db"

