from __future__ import annotations

from pathlib import Path

import yaml

_ALLOWED_FETCH_DEPTHS = {0, 1}


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


def _normalize_fetch_depth(raw: object) -> int:
    if isinstance(raw, bool):
        raise AssertionError(f"fetch-depth must be integer-like, got bool ({raw!r})")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        token = raw.strip()
        if token.isdigit():
            return int(token)
    raise AssertionError(f"fetch-depth must be int or numeric string, got {raw!r}")


def test_checkout_steps_must_define_explicit_fetch_depth() -> None:
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

                step_label = step.get("name") or f"step[{idx}]"
                with_block = step.get("with")
                if not isinstance(with_block, dict):
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: checkout step must define with.fetch-depth"
                    )
                    continue

                if "fetch-depth" not in with_block:
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: missing with.fetch-depth"
                    )
                    continue

                try:
                    fetch_depth = _normalize_fetch_depth(with_block.get("fetch-depth"))
                except AssertionError as exc:
                    violations.append(f"{rel} job '{job_id}' {step_label}: {exc}")
                    continue

                if fetch_depth not in _ALLOWED_FETCH_DEPTHS:
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: fetch-depth={fetch_depth} "
                        f"not in {sorted(_ALLOWED_FETCH_DEPTHS)}"
                    )

    assert checkout_steps > 0, "No actions/checkout steps found under .github/workflows"
    assert not violations, (
        "actions/checkout steps must declare explicit bounded fetch-depth:\n"
        + "\n".join(violations)
    )
