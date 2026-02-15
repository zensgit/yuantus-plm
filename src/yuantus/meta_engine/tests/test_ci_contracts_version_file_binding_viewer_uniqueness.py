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


def test_verify_version_files_uses_unique_viewer_username_per_run() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_version_files.sh"
    assert script.is_file(), f"Missing {script}"
    text = _read(script)

    assert 'VIEWER_USER="viewer-$TS"' in text, (
        "verify_version_files.sh should generate a per-run viewer username to avoid "
        "cross-run identity collisions."
    )
    assert '--username "$VIEWER_USER"' in text, (
        "verify_version_files.sh should seed identity using the per-run viewer username."
    )
    assert "--roles viewer --no-superuser" in text, (
        "verify_version_files.sh viewer seed should explicitly set --no-superuser "
        "for consistent login behavior."
    )
    assert '\\"username\\":\\"$VIEWER_USER\\"' in text, (
        "verify_version_files.sh viewer login payload should use per-run viewer username."
    )
    assert '\\"username\\":\\"viewer\\"' not in text, (
        "verify_version_files.sh should not hardcode viewer username in login payload."
    )
