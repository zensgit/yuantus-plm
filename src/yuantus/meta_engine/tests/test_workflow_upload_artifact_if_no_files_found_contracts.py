from __future__ import annotations

from pathlib import Path

import yaml

_ALLOWED_IF_NO_FILES_FOUND = {"warn", "error", "ignore"}


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


def test_workflow_upload_artifact_steps_define_if_no_files_found_policy() -> None:
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
                with_payload = step.get("with")
                assert isinstance(with_payload, dict), (
                    f"{rel} job '{job_id}' step#{idx + 1} upload-artifact must define with mapping"
                )
                policy = with_payload.get("if-no-files-found")
                assert isinstance(policy, str) and policy.strip(), (
                    f"{rel} job '{job_id}' step#{idx + 1} upload-artifact must define non-empty if-no-files-found"
                )
                assert policy in _ALLOWED_IF_NO_FILES_FOUND, (
                    f"{rel} job '{job_id}' step#{idx + 1} upload-artifact has invalid "
                    f"if-no-files-found={policy!r}; allowed={sorted(_ALLOWED_IF_NO_FILES_FOUND)}"
                )

    assert checked > 0, "No actions/upload-artifact steps found under .github/workflows"
