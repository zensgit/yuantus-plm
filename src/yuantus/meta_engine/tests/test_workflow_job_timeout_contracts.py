from __future__ import annotations

from pathlib import Path

import yaml

_MIN_TIMEOUT_MINUTES = 1
_MAX_TIMEOUT_MINUTES = 120


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


def _normalize_timeout_minutes(*, workflow_rel: str, job_name: str, timeout_value: object) -> int:
    if isinstance(timeout_value, bool):
        raise AssertionError(
            f"{workflow_rel} job '{job_name}' timeout-minutes must be integer-like, got bool"
        )

    if isinstance(timeout_value, int):
        timeout_minutes = timeout_value
    elif isinstance(timeout_value, str):
        raw = timeout_value.strip()
        assert raw.isdigit(), (
            f"{workflow_rel} job '{job_name}' timeout-minutes must be numeric string/int, "
            f"got {timeout_value!r}"
        )
        timeout_minutes = int(raw)
    else:
        raise AssertionError(
            f"{workflow_rel} job '{job_name}' timeout-minutes must be string/int, "
            f"got {type(timeout_value).__name__}"
        )

    assert _MIN_TIMEOUT_MINUTES <= timeout_minutes <= _MAX_TIMEOUT_MINUTES, (
        f"{workflow_rel} job '{job_name}' timeout-minutes={timeout_minutes} out of range "
        f"[{_MIN_TIMEOUT_MINUTES}, {_MAX_TIMEOUT_MINUTES}]"
    )
    return timeout_minutes


def test_all_workflow_jobs_declare_bounded_timeout_minutes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        jobs = payload.get("jobs")
        assert isinstance(jobs, dict), f"{rel} must declare jobs mapping"
        assert jobs, f"{rel} must declare at least one job"

        for job_name, job_payload in jobs.items():
            assert isinstance(job_payload, dict), f"{rel} job '{job_name}' must be a mapping"
            assert "timeout-minutes" in job_payload, (
                f"{rel} job '{job_name}' must declare timeout-minutes"
            )
            _normalize_timeout_minutes(
                workflow_rel=rel,
                job_name=str(job_name),
                timeout_value=job_payload["timeout-minutes"],
            )
