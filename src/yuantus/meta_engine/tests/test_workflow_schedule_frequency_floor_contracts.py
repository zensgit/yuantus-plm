from __future__ import annotations

from pathlib import Path
from typing import Any

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


def _workflow_on_block(payload: dict) -> Any:
    # PyYAML may parse top-level 'on' as boolean True with YAML 1.1 rules.
    return payload.get("on") if "on" in payload else payload.get(True)


def _extract_schedule_crons(node: Any) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key) == "schedule" and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and isinstance(item.get("cron"), str):
                        out.append(item["cron"].strip())
            out.extend(_extract_schedule_crons(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(_extract_schedule_crons(item))
    return out


def _is_fixed_minute_field(token: str) -> bool:
    if not token.isdigit():
        return False
    value = int(token)
    return 0 <= value <= 59


def test_workflow_schedule_cron_frequency_is_hourly_or_slower() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    violations: list[str] = []

    for workflow in workflows:
        payload = _load_yaml(workflow)
        on_block = _workflow_on_block(payload)
        if on_block is None:
            continue

        crons = _extract_schedule_crons(on_block)
        if not crons:
            continue

        rel = workflow.relative_to(repo_root).as_posix()
        for cron in crons:
            checked += 1
            fields = cron.split()
            if len(fields) != 5:
                violations.append(f"{rel} -> {cron} (expected 5 fields)")
                continue
            minute = fields[0]
            if not _is_fixed_minute_field(minute):
                violations.append(
                    f"{rel} -> {cron} (minute field must be fixed numeric literal 0-59)"
                )

    assert checked > 0, "No schedule cron expressions found under .github/workflows"
    assert not violations, (
        "Workflow schedule must be hourly-or-slower (no minute-level cadence):\n"
        + "\n".join(violations)
    )
