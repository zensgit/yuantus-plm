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


def _get_on(payload: dict) -> dict:
    on = payload.get("on")
    if isinstance(on, dict):
        return on
    if True in payload and isinstance(payload[True], dict):
        # PyYAML YAML 1.1 parses `on` as bool True.
        return payload[True]
    return {}


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def test_workflow_dispatch_inputs_have_stable_metadata_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        workflow_dispatch = _get_on(payload).get("workflow_dispatch")
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

            description = input_payload.get("description")
            assert _is_non_empty_string(description), (
                f"{rel} workflow_dispatch.inputs.{input_name} must declare non-empty description"
            )

            assert "required" in input_payload, (
                f"{rel} workflow_dispatch.inputs.{input_name} must declare required"
            )
            required = input_payload["required"]
            assert isinstance(required, bool), (
                f"{rel} workflow_dispatch.inputs.{input_name}.required must be boolean"
            )

            input_type = input_payload.get("type")
            assert _is_non_empty_string(input_type), (
                f"{rel} workflow_dispatch.inputs.{input_name} must declare non-empty type"
            )

            if required is False:
                assert "default" in input_payload, (
                    f"{rel} workflow_dispatch.inputs.{input_name} is optional; default is required"
                )

            if input_type == "choice":
                options = input_payload.get("options")
                assert isinstance(options, list) and options, (
                    f"{rel} workflow_dispatch.inputs.{input_name} (choice) must declare non-empty options list"
                )
                normalized_options: set[str] = set()
                for idx, option in enumerate(options):
                    assert _is_non_empty_string(option), (
                        f"{rel} workflow_dispatch.inputs.{input_name}.options[{idx}] must be non-empty string"
                    )
                    normalized = option.strip()
                    assert normalized not in normalized_options, (
                        f"{rel} workflow_dispatch.inputs.{input_name}.options contains duplicate option '{normalized}'"
                    )
                    normalized_options.add(normalized)

                if "default" in input_payload:
                    default = input_payload["default"]
                    assert _is_non_empty_string(default), (
                        f"{rel} workflow_dispatch.inputs.{input_name}.default must be non-empty string for choice type"
                    )
                    assert default.strip() in normalized_options, (
                        f"{rel} workflow_dispatch.inputs.{input_name}.default must be one of options"
                    )
