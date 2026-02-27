from __future__ import annotations

from pathlib import Path

import yaml

_CHECKOUT_VERSION_PREFIX = "actions/checkout@v4"


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


def test_checkout_steps_use_v4_baseline() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checkout_steps = 0
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
                checkout_steps += 1
                if not uses.startswith(_CHECKOUT_VERSION_PREFIX):
                    step_label = step.get("name") or f"step[{idx}]"
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: uses={uses!r} "
                        f"must start with {_CHECKOUT_VERSION_PREFIX!r}"
                    )

    assert checkout_steps > 0, "No actions/checkout steps found under .github/workflows"
    assert not violations, (
        "Checkout steps must pin actions/checkout to v4 baseline:\n" + "\n".join(violations)
    )
