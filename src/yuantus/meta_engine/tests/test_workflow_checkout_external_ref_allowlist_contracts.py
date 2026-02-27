from __future__ import annotations

from pathlib import Path

import yaml

_ALLOWED_EXTERNAL_CHECKOUT_REFS = {
    "zensgit/CADGameFusion": {"main"},
    "zensgit/cad-ml-platform": {"main"},
}


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


def test_external_checkout_refs_are_allowlisted_per_repository() -> None:
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
                normalized_repo = repository.strip()
                allowed_refs = _ALLOWED_EXTERNAL_CHECKOUT_REFS.get(normalized_repo)
                step_label = step.get("name") or f"step[{idx}]"
                if not allowed_refs:
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: repository {normalized_repo!r} "
                        "missing from external ref allowlist map"
                    )
                    continue

                ref = with_block.get("ref")
                if not (isinstance(ref, str) and ref.strip()):
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: external checkout ({normalized_repo}) "
                        "must define non-empty with.ref"
                    )
                    continue

                normalized_ref = ref.strip()
                if normalized_ref not in allowed_refs:
                    violations.append(
                        f"{rel} job '{job_id}' {step_label}: external checkout ({normalized_repo}) "
                        f"ref={normalized_ref!r} not in allowlist {sorted(allowed_refs)}"
                    )

    assert checked > 0, "No external actions/checkout steps found under .github/workflows"
    assert not violations, (
        "External checkout refs must match per-repository allowlist:\n" + "\n".join(violations)
    )
