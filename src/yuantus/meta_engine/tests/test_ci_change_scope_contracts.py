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


def test_ci_change_scope_has_script_triggers_and_is_documented() -> None:
    repo_root = _find_repo_root(Path(__file__))

    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    regression_yml = repo_root / ".github" / "workflows" / "regression.yml"
    runbook = repo_root / "docs" / "RUNBOOK_CI_CHANGE_SCOPE.md"
    debug_script = repo_root / "scripts" / "ci_change_scope_debug.sh"

    assert debug_script.is_file(), "Expected local debug helper: scripts/ci_change_scope_debug.sh"

    ci_text = _read(ci_yml)
    assert "scripts/*.sh|scripts/*.py" in ci_text, (
        "Expected CI detect_changes to run contracts on scripts changes "
        "(scripts/*.sh|scripts/*.py)"
    )
    for token in ("run_plugin_tests_reason", "run_playwright_reason", "run_contracts_reason"):
        assert token in ci_text, f"Expected CI job summary to include: {token}"

    regression_text = _read(regression_yml)
    # PR cost rule: workflow-only edits shouldn't trigger heavy jobs by default.
    assert "regression_workflow_changed" in regression_text

    runbook_text = _read(runbook)
    assert "scripts/ci_change_scope_debug.sh" in runbook_text, (
        "Expected runbook to document scripts/ci_change_scope_debug.sh"
    )

