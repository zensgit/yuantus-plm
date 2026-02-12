from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + src/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_db_command_declares_identity_and_db_url_flags() -> None:
    repo_root = _find_repo_root(Path(__file__))
    cli_py = repo_root / "src" / "yuantus" / "cli.py"
    assert cli_py.is_file()
    text = _read(cli_py)

    assert '@app.command("db")' in text, "Missing Typer command registration: @app.command('db')"
    assert "--db-url" in text, "Missing CLI flag: --db-url"
    assert "--identity/--no-identity" in text, "Missing CLI flag: --identity/--no-identity"


def test_db_command_rejects_conflicting_identity_flags_guard_present() -> None:
    repo_root = _find_repo_root(Path(__file__))
    cli_py = repo_root / "src" / "yuantus" / "cli.py"
    text = _read(cli_py)

    assert "if db_url and identity" in text, "Missing mutual exclusion guard: if db_url and identity"
    assert "mutually exclusive" in text, "Missing mutual exclusion error message hint"


def test_db_command_identity_targets_identity_database_url_or_falls_back() -> None:
    repo_root = _find_repo_root(Path(__file__))
    cli_py = repo_root / "src" / "yuantus" / "cli.py"
    text = _read(cli_py)

    # Keep this as a flexible string contract rather than a strict AST check.
    assert (
        "settings.IDENTITY_DATABASE_URL or settings.DATABASE_URL" in text
    ), "Missing identity URL resolution: settings.IDENTITY_DATABASE_URL or settings.DATABASE_URL"
    assert (
        'env["YUANTUS_DATABASE_URL"] = resolved_url' in text
    ), "Missing env override for Alembic target: env['YUANTUS_DATABASE_URL'] = resolved_url"


def test_db_command_db_url_override_targets_explicit_url() -> None:
    repo_root = _find_repo_root(Path(__file__))
    cli_py = repo_root / "src" / "yuantus" / "cli.py"
    text = _read(cli_py)

    assert (
        'env["YUANTUS_DATABASE_URL"] = db_url' in text
    ), "Missing db-url env override: env['YUANTUS_DATABASE_URL'] = db_url"

    # Ensure the override is wired to the Alembic invocation.
    assert "subprocess.run" in text, "Missing subprocess.run invocation"
    assert "env=env" in text, "Missing subprocess.run(... env=env) wiring"
