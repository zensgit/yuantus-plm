from __future__ import annotations

from pathlib import Path

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


def test_all_workflows_define_safe_concurrency_group() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        concurrency = payload.get("concurrency")
        assert isinstance(concurrency, dict), f"{rel} must declare top-level concurrency mapping"

        group = concurrency.get("group")
        assert isinstance(group, str) and group.strip(), f"{rel} concurrency.group must be non-empty"
        assert "github.workflow" in group, f"{rel} concurrency.group should include github.workflow"
        assert "github.ref" in group, f"{rel} concurrency.group should include github.ref"

        cancel = concurrency.get("cancel-in-progress")
        assert cancel is True, f"{rel} concurrency.cancel-in-progress must be true"
