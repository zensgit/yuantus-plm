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


def test_workflow_label_overrides_are_documented_and_present() -> None:
    repo_root = _find_repo_root(Path(__file__))

    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    regression_yml = repo_root / ".github" / "workflows" / "regression.yml"
    runbook = repo_root / "docs" / "RUNBOOK_CI_CHANGE_SCOPE.md"

    ci_text = _read(ci_yml)
    regression_text = _read(regression_yml)
    runbook_text = _read(runbook)

    # CI: global force full label.
    assert "ci:full" in ci_text
    assert "force_full" in ci_text

    # Regression: force labels for integration and CADGF.
    for label in ("ci:full", "regression:force", "cadgf:force"):
        assert label in regression_text

    # Runbook must document how to use the overrides.
    for token in ("ci:full", "regression:force", "cadgf:force", "gh pr edit", "gh workflow run"):
        assert token in runbook_text

