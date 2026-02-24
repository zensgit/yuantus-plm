from __future__ import annotations

from pathlib import Path

import yaml

_EXPECTED_GROUP_TEMPLATE = "${{ github.workflow }}-${{ github.ref }}"


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


def test_workflow_concurrency_group_uses_repo_standard_template() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        concurrency = payload.get("concurrency")
        assert isinstance(concurrency, dict), f"{rel} must declare top-level concurrency mapping"

        group = concurrency.get("group")
        assert group == _EXPECTED_GROUP_TEMPLATE, (
            f"{rel} concurrency.group must match repo template "
            f"{_EXPECTED_GROUP_TEMPLATE!r}; got {group!r}"
        )

        cancel = concurrency.get("cancel-in-progress")
        assert cancel is True, f"{rel} concurrency.cancel-in-progress must be true"
