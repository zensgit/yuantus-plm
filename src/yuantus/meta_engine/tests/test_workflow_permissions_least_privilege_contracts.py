from __future__ import annotations

from pathlib import Path

import yaml

_ACTIONS_WRITE_ALLOWLIST = {"strict-gate-recent-perf-regression.yml"}


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


def test_workflow_permissions_follow_least_privilege_baseline() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        name = workflow.name
        payload = _load_yaml(workflow)
        permissions = payload.get("permissions")
        assert isinstance(permissions, dict), f"{rel} must declare top-level permissions mapping"

        contents = permissions.get("contents")
        actions = permissions.get("actions")

        assert contents == "read", f"{rel} must pin contents to read; got {contents!r}"
        if name in _ACTIONS_WRITE_ALLOWLIST:
            assert actions == "write", f"{rel} is in actions-write allowlist and must set actions=write"
        else:
            assert actions == "read", (
                f"{rel} is not in actions-write allowlist and must set actions=read; "
                f"got {actions!r}"
            )
