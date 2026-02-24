from __future__ import annotations

from pathlib import Path
from typing import Any

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


def _to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def test_upload_artifact_steps_define_retention_days() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    missing: list[str] = []
    invalid: list[str] = []

    for wf in workflows:
        payload = _load_yaml(wf)
        jobs = payload.get("jobs")
        if not isinstance(jobs, dict):
            continue

        rel = wf.relative_to(repo_root).as_posix()
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for idx, step in enumerate(steps, 1):
                if not isinstance(step, dict):
                    continue
                uses = str(step.get("uses", "")).strip()
                if uses != "actions/upload-artifact@v4":
                    continue
                checked += 1
                with_map = step.get("with")
                if not isinstance(with_map, dict):
                    missing.append(f"{rel}:{job_name}:step#{idx}")
                    continue
                if "retention-days" not in with_map:
                    missing.append(f"{rel}:{job_name}:step#{idx}")
                    continue
                days = _to_int(with_map.get("retention-days"))
                if days is None or not (1 <= days <= 30):
                    invalid.append(
                        f"{rel}:{job_name}:step#{idx} retention-days={with_map.get('retention-days')!r}"
                    )

    assert checked > 0, "No actions/upload-artifact@v4 steps found under .github/workflows"
    assert not missing, (
        "Upload artifact steps must define with.retention-days:\n"
        + "\n".join(missing)
    )
    assert not invalid, (
        "Upload artifact retention-days must be integer in [1, 30]:\n"
        + "\n".join(invalid)
    )
