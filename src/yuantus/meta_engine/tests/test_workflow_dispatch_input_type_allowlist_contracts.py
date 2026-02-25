from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ALLOWED_DISPATCH_INPUT_TYPES = {
    "boolean",
    "choice",
    "environment",
    "number",
    "string",
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


def _workflow_on_block(payload: dict) -> Any:
    # PyYAML may parse top-level 'on' as boolean True with YAML 1.1 rules.
    return payload.get("on") if "on" in payload else payload.get(True)


def test_workflow_dispatch_input_types_are_allowlisted() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    violations: list[str] = []

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

        for input_name, input_payload in inputs.items():
            if not isinstance(input_payload, dict):
                continue
            checked += 1
            input_type = input_payload.get("type")
            if not isinstance(input_type, str) or not input_type.strip():
                violations.append(f"{rel} -> workflow_dispatch.inputs.{input_name} missing non-empty type")
                continue
            normalized_type = input_type.strip()
            if normalized_type not in _ALLOWED_DISPATCH_INPUT_TYPES:
                violations.append(
                    f"{rel} -> workflow_dispatch.inputs.{input_name}.type={normalized_type!r} "
                    f"not in {sorted(_ALLOWED_DISPATCH_INPUT_TYPES)}"
                )

    assert checked > 0, "No workflow_dispatch inputs found under .github/workflows"
    assert not violations, "workflow_dispatch input type allowlist violations:\n" + "\n".join(violations)
