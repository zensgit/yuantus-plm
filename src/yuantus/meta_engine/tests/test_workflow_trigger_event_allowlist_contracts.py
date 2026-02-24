from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ALLOWED_EVENTS = {"pull_request", "push", "schedule", "workflow_dispatch"}


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


def test_workflow_trigger_events_are_allowlisted() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        on_block = _workflow_on_block(payload)
        assert isinstance(on_block, dict), f"{rel} on block must be a mapping"
        assert on_block, f"{rel} on block must not be empty"

        event_names = {str(k) for k in on_block.keys()}
        unexpected = sorted(event_names - _ALLOWED_EVENTS)
        assert not unexpected, (
            f"{rel} declares unsupported trigger events {unexpected}; "
            f"allowed={sorted(_ALLOWED_EVENTS)}"
        )
