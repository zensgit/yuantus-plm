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


def _is_full_history_checkout_step(step: dict) -> bool:
    uses = step.get("uses")
    if not isinstance(uses, str) or not uses.startswith("actions/checkout@"):
        return False

    with_payload = step.get("with")
    if not isinstance(with_payload, dict):
        return False
    fetch_depth = with_payload.get("fetch-depth")
    return fetch_depth in {0, "0"}


def _job_uses_git_diff(job_payload: dict) -> bool:
    steps = job_payload.get("steps")
    if not isinstance(steps, list):
        return False
    for step in steps:
        if not isinstance(step, dict):
            continue
        run_script = step.get("run")
        if isinstance(run_script, str) and "git diff" in run_script:
            return True
    return False


def test_jobs_using_git_diff_must_checkout_with_fetch_depth_zero() -> None:
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
            if not _job_uses_git_diff(job_payload):
                continue
            checked += 1

            steps = job_payload.get("steps")
            assert isinstance(steps, list), f"{rel} job '{job_id}' must declare steps list"
            assert any(
                _is_full_history_checkout_step(step) for step in steps if isinstance(step, dict)
            ), (
                f"{rel} job '{job_id}' uses git diff and must include actions/checkout with "
                "with.fetch-depth: 0"
            )

    assert checked > 0, "No jobs using git diff were found to validate"
