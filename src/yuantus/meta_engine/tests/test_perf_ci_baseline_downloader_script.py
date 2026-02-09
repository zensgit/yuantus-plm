from __future__ import annotations

import subprocess
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


def test_perf_ci_download_baselines_script_is_syntax_valid_and_has_help() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "perf_ci_download_baselines.sh"
    assert script.is_file(), f"Missing script: {script}"

    # Syntax check (no execution).
    cp = subprocess.run(["bash", "-n", str(script)], text=True, capture_output=True)  # noqa: S603,S607
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr

    # Help output should not require env vars.
    cp2 = subprocess.run(["bash", str(script), "--help"], text=True, capture_output=True)  # noqa: S603,S607
    assert cp2.returncode == 0, cp2.stdout + "\n" + cp2.stderr
    assert "Usage:" in (cp2.stdout or "")
    assert "--workflow" in (cp2.stdout or "")
    assert "--artifact" in (cp2.stdout or "")

