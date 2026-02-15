from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_verify_mbom_convert_prefers_provided_db_url_over_runtime_resolution() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_mbom_convert.sh"
    assert script.is_file(), f"Missing {script}"
    text = _read(script)

    assert 'elif [[ -z "$DB_URL" ]]; then' in text, (
        "verify_mbom_convert.sh should only resolve tenant DB URL when DB_URL is absent."
    )
    assert "resolve_database_url" in text, (
        "verify_mbom_convert.sh should keep resolve_database_url fallback for missing DB_URL."
    )
    assert text.count('elif [[ -z "$DB_URL" ]]; then') >= 2, (
        "verify_mbom_convert.sh should guard both db-per-tenant-org and db-per-tenant paths."
    )

