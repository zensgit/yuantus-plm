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


def _load_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    assert isinstance(payload, dict), f"workflow did not parse as mapping: {path}"
    return payload


def test_workflow_upload_artifact_steps_run_under_always_condition() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        jobs = payload.get("jobs")
        assert isinstance(jobs, dict), f"{rel} must declare jobs mapping"

        for job_id, job_payload in jobs.items():
            if not isinstance(job_payload, dict):
                continue
            steps = job_payload.get("steps")
            if not isinstance(steps, list):
                continue

            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if not isinstance(uses, str) or not uses.startswith("actions/upload-artifact@"):
                    continue

                checked += 1
                step_if = step.get("if")
                assert isinstance(step_if, str) and step_if.strip(), (
                    f"{rel} job '{job_id}' step#{idx + 1} upload-artifact must define non-empty if condition"
                )
                assert "always()" in step_if, (
                    f"{rel} job '{job_id}' step#{idx + 1} upload-artifact if condition "
                    f"must include always(); got {step_if!r}"
                )

    assert checked > 0, "No actions/upload-artifact steps found under .github/workflows"
