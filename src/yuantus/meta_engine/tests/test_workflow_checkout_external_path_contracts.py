from __future__ import annotations

from pathlib import PurePosixPath, Path

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


def _is_safe_relative_path(raw: str) -> bool:
    token = raw.strip()
    if not token:
        return False
    p = PurePosixPath(token)
    if p.is_absolute():
        return False
    parts = p.parts
    if not parts:
        return False
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return True


def test_external_checkout_steps_must_pin_explicit_safe_path() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    violations: list[str] = []

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
                if not (isinstance(uses, str) and uses.startswith("actions/checkout@")):
                    continue

                with_block = step.get("with")
                if not isinstance(with_block, dict):
                    continue
                repository = with_block.get("repository")
                if not (isinstance(repository, str) and repository.strip()):
                    continue

                checked += 1
                step_label = step.get("name") or f"step[{idx}]"
                path_value = with_block.get("path")
                if not isinstance(path_value, str):
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: external checkout "
                        f"({repository}) must define string with.path"
                    )
                    continue
                if not _is_safe_relative_path(path_value):
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: with.path={path_value!r} "
                        "must be a safe non-empty relative path"
                    )

    assert checked > 0, "No external actions/checkout steps found under .github/workflows"
    assert not violations, (
        "External checkout steps must pin explicit safe with.path:\n" + "\n".join(violations)
    )
