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


def _workflow_on_block(payload: dict) -> dict:
    if isinstance(payload.get("on"), dict):
        return payload["on"]
    if True in payload and isinstance(payload[True], dict):
        # PyYAML YAML 1.1 may parse top-level `on` as bool True.
        return payload[True]
    return {}


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def test_workflow_dispatch_input_defaults_match_declared_types() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        workflow_dispatch = _workflow_on_block(payload).get("workflow_dispatch")
        if workflow_dispatch is None:
            continue
        assert isinstance(workflow_dispatch, dict), (
            f"{rel} workflow_dispatch must be a mapping when present"
        )

        inputs = workflow_dispatch.get("inputs")
        if inputs is None:
            continue
        assert isinstance(inputs, dict), f"{rel} workflow_dispatch.inputs must be a mapping"

        for input_name, input_payload in inputs.items():
            assert isinstance(input_payload, dict), (
                f"{rel} workflow_dispatch.inputs.{input_name} must be a mapping"
            )
            if "default" not in input_payload:
                continue

            input_type = input_payload.get("type")
            default_value = input_payload["default"]
            assert isinstance(input_type, str) and input_type.strip(), (
                f"{rel} workflow_dispatch.inputs.{input_name} must define type"
            )

            if input_type == "boolean":
                assert isinstance(default_value, bool), (
                    f"{rel} workflow_dispatch.inputs.{input_name} default must be boolean for type=boolean"
                )
            elif input_type in {"string", "choice", "environment"}:
                assert isinstance(default_value, str), (
                    f"{rel} workflow_dispatch.inputs.{input_name} default must be string for type={input_type}"
                )
            elif input_type == "number":
                assert _is_number(default_value), (
                    f"{rel} workflow_dispatch.inputs.{input_name} default must be numeric for type=number"
                )
