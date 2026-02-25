from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_INPUT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


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
    # PyYAML may parse top-level `on` as bool True under YAML 1.1 rules.
    return payload.get("on") if "on" in payload else payload.get(True)


def test_workflow_dispatch_input_names_use_stable_snake_case() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        on_block = _workflow_on_block(payload)
        if not isinstance(on_block, dict):
            continue

        workflow_dispatch = on_block.get("workflow_dispatch")
        if not isinstance(workflow_dispatch, dict):
            continue

        inputs = workflow_dispatch.get("inputs")
        if not isinstance(inputs, dict):
            continue

        for input_name in inputs.keys():
            assert isinstance(input_name, str), (
                f"{rel} workflow_dispatch input name must be string; got {type(input_name).__name__}"
            )
            assert _INPUT_NAME_RE.match(input_name), (
                f"{rel} workflow_dispatch input '{input_name}' must match snake_case pattern "
                "'^[a-z][a-z0-9_]*$'"
            )
            assert "__" not in input_name, (
                f"{rel} workflow_dispatch input '{input_name}' must not contain consecutive underscores"
            )
