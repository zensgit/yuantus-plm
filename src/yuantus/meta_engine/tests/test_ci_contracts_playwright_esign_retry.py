from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_ci_playwright_esign_job_has_retry_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    ci = repo_root / ".github" / "workflows" / "ci.yml"
    assert ci.is_file(), f"Missing workflow: {ci}"
    text = _read(ci)

    for token in (
        "playwright-esign:",
        "Playwright e-sign smoke",
        "set -euo pipefail",
        "attempts=2",
        "retry_delay_sec=5",
        "for attempt in $(seq 1 \"${attempts}\")",
        "Playwright e-sign smoke attempt ${attempt}/${attempts}",
        "if npx playwright test; then",
        "Playwright e-sign smoke failed on attempt ${attempt}; retry in ${retry_delay_sec}s...",
        "sleep \"${retry_delay_sec}\"",
        "ERROR: Playwright e-sign smoke failed after ${attempts} attempts",
    ):
        assert token in text, f"ci workflow missing Playwright retry token: {token}"
