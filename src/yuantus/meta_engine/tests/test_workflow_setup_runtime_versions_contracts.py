from __future__ import annotations

from pathlib import Path

import yaml

_EXPECTED_SETUP_PYTHON = ("actions/setup-python@v5", "3.11")
_EXPECTED_SETUP_NODE = ("actions/setup-node@v4", "20")


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


def test_workflow_setup_runtime_versions_are_repo_standardized() -> None:
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
                with_payload = step.get("with")
                if not isinstance(uses, str):
                    continue

                if uses == _EXPECTED_SETUP_PYTHON[0]:
                    checked += 1
                    assert isinstance(with_payload, dict), (
                        f"{rel} job '{job_id}' step#{idx + 1} setup-python must define with mapping"
                    )
                    py_ver = with_payload.get("python-version")
                    assert isinstance(py_ver, str) and py_ver.strip(), (
                        f"{rel} job '{job_id}' step#{idx + 1} setup-python must define python-version"
                    )
                    assert py_ver == _EXPECTED_SETUP_PYTHON[1], (
                        f"{rel} job '{job_id}' step#{idx + 1} setup-python "
                        f"must pin python-version={_EXPECTED_SETUP_PYTHON[1]!r}; got {py_ver!r}"
                    )

                if uses == _EXPECTED_SETUP_NODE[0]:
                    checked += 1
                    assert isinstance(with_payload, dict), (
                        f"{rel} job '{job_id}' step#{idx + 1} setup-node must define with mapping"
                    )
                    node_ver = with_payload.get("node-version")
                    assert isinstance(node_ver, str) and node_ver.strip(), (
                        f"{rel} job '{job_id}' step#{idx + 1} setup-node must define node-version"
                    )
                    assert node_ver == _EXPECTED_SETUP_NODE[1], (
                        f"{rel} job '{job_id}' step#{idx + 1} setup-node "
                        f"must pin node-version={_EXPECTED_SETUP_NODE[1]!r}; got {node_ver!r}"
                    )

    assert checked > 0, "No setup-python/setup-node steps checked under .github/workflows"
