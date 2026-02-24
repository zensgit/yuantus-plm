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


def test_upload_artifact_steps_have_unique_nonempty_names_per_workflow() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        jobs = payload.get("jobs")
        assert isinstance(jobs, dict), f"{rel} must declare jobs mapping"

        names: list[str] = []
        for job_name, job_payload in jobs.items():
            assert isinstance(job_payload, dict), f"{rel} job '{job_name}' must be a mapping"
            steps = job_payload.get("steps") or []
            assert isinstance(steps, list), f"{rel} job '{job_name}' steps must be a list"

            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                if not (isinstance(uses, str) and uses.startswith("actions/upload-artifact@v4")):
                    continue

                with_block = step.get("with")
                assert isinstance(with_block, dict), (
                    f"{rel} job '{job_name}' step[{idx}] upload-artifact must define 'with'"
                )
                artifact_name = with_block.get("name")
                assert isinstance(artifact_name, str) and artifact_name.strip(), (
                    f"{rel} job '{job_name}' step[{idx}] upload-artifact must define non-empty with.name"
                )
                names.append(artifact_name.strip())

        duplicates = sorted({name for name in names if names.count(name) > 1})
        assert not duplicates, (
            f"{rel} has duplicate upload-artifact names: {duplicates}; names must be unique per workflow"
        )
