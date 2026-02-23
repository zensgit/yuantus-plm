from __future__ import annotations

from pathlib import Path

import yaml


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def test_all_workflow_yaml_files_are_parseable_and_have_core_keys() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflow_dir = repo_root / ".github" / "workflows"
    workflows = sorted(workflow_dir.glob("*.yml"))
    assert workflows, f"No workflow files found under {workflow_dir}"

    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8", errors="replace")
        try:
            doc = yaml.safe_load(text)
        except Exception as exc:  # pragma: no cover - assertion below handles failure
            raise AssertionError(f"workflow YAML parse failed: {workflow}: {exc}") from exc

        assert isinstance(doc, dict), f"workflow must parse to a mapping: {workflow}"
        assert doc.get("name"), f"workflow missing non-empty name: {workflow}"

        # PyYAML may parse top-level 'on' as boolean True with YAML 1.1 rules.
        on_key = "on" if "on" in doc else True
        assert on_key in doc, f"workflow missing trigger definition ('on'): {workflow}"
        assert doc[on_key] is not None, f"workflow 'on' must not be null: {workflow}"

        jobs = doc.get("jobs")
        assert isinstance(jobs, dict), f"workflow jobs must be a mapping: {workflow}"
        assert jobs, f"workflow must define at least one job: {workflow}"
