from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ALLOWED_PUSH_BRANCHES = {"main", "master"}
_REQUIRED_PUSH_BRANCH = "main"


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


def _workflow_on_block(payload: dict) -> Any:
    # PyYAML may parse top-level 'on' as boolean True with YAML 1.1 rules.
    return payload.get("on") if "on" in payload else payload.get(True)


def test_workflow_push_branches_are_allowlisted() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked_workflows = 0

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        on_block = _workflow_on_block(payload)
        assert isinstance(on_block, dict), f"{rel} on block must be a mapping"

        if "push" not in on_block:
            continue

        checked_workflows += 1
        push_block = on_block["push"]
        assert isinstance(push_block, dict), (
            f"{rel} on.push must be a mapping with explicit branches allowlist"
        )
        assert "branches-ignore" not in push_block, (
            f"{rel} on.push must not use branches-ignore; use branches allowlist only"
        )
        branches = push_block.get("branches")
        assert isinstance(branches, list), (
            f"{rel} on.push.branches must be a non-empty list of literal branch names"
        )
        assert branches, f"{rel} on.push.branches must not be empty"

        normalized: list[str] = []
        for idx, raw in enumerate(branches):
            assert isinstance(raw, str), (
                f"{rel} on.push.branches[{idx}] must be string, got {type(raw).__name__}"
            )
            branch = raw.strip()
            assert branch, f"{rel} on.push.branches[{idx}] must not be empty"
            normalized.append(branch)

        duplicates = sorted({b for b in normalized if normalized.count(b) > 1})
        assert not duplicates, f"{rel} on.push.branches contains duplicates: {duplicates}"

        unexpected = sorted(set(normalized) - _ALLOWED_PUSH_BRANCHES)
        assert not unexpected, (
            f"{rel} on.push.branches has unsupported branch(es) {unexpected}; "
            f"allowed={sorted(_ALLOWED_PUSH_BRANCHES)}"
        )
        assert _REQUIRED_PUSH_BRANCH in normalized, (
            f"{rel} on.push.branches must include '{_REQUIRED_PUSH_BRANCH}'"
        )

    assert checked_workflows > 0, "No workflows with on.push found under .github/workflows"
