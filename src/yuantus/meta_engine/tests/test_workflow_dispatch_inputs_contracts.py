from __future__ import annotations

from pathlib import Path

import yaml

_ALLOWED_INPUT_TYPES = {"string", "boolean", "choice", "number", "environment"}


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


def _workflow_on_block(payload: dict) -> object:
    # PyYAML may parse the key "on" as boolean True under YAML 1.1 rules.
    return payload.get("on", payload.get(True))


def test_workflow_dispatch_inputs_define_explicit_types() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        on_block = _workflow_on_block(payload)
        if not isinstance(on_block, dict):
            continue
        dispatch = on_block.get("workflow_dispatch")
        if not isinstance(dispatch, dict):
            continue
        inputs = dispatch.get("inputs")
        if inputs is None:
            continue
        assert isinstance(inputs, dict), f"{rel} workflow_dispatch.inputs must be a mapping"

        for input_name, input_cfg in inputs.items():
            assert isinstance(input_cfg, dict), (
                f"{rel} workflow_dispatch input '{input_name}' must be a mapping"
            )
            assert "type" in input_cfg, (
                f"{rel} workflow_dispatch input '{input_name}' must declare explicit type"
            )
            input_type = input_cfg["type"]
            assert isinstance(input_type, str), (
                f"{rel} workflow_dispatch input '{input_name}' type must be a string"
            )
            assert input_type in _ALLOWED_INPUT_TYPES, (
                f"{rel} workflow_dispatch input '{input_name}' type={input_type!r} unsupported; "
                f"allowed={sorted(_ALLOWED_INPUT_TYPES)}"
            )
