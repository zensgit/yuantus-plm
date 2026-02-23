from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CRON_FIELD_BOUNDS = (
    (0, 59),  # minute
    (0, 23),  # hour
    (1, 31),  # day of month
    (1, 12),  # month
    (0, 7),  # day of week (0 or 7 for Sunday)
)


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


def _validate_cron_value(token: str, lower: int, upper: int) -> bool:
    if not token.isdigit():
        return False
    value = int(token)
    return lower <= value <= upper


def _validate_cron_atom(atom: str, lower: int, upper: int) -> bool:
    if not atom:
        return False

    if atom == "*":
        return True

    if "/" in atom:
        base, step = atom.split("/", 1)
        if not step.isdigit() or int(step) <= 0:
            return False
        if base == "*":
            return True
        if "-" in base:
            start, end = base.split("-", 1)
            return (
                _validate_cron_value(start, lower, upper)
                and _validate_cron_value(end, lower, upper)
                and int(start) <= int(end)
            )
        return _validate_cron_value(base, lower, upper)

    if "-" in atom:
        start, end = atom.split("-", 1)
        return (
            _validate_cron_value(start, lower, upper)
            and _validate_cron_value(end, lower, upper)
            and int(start) <= int(end)
        )

    return _validate_cron_value(atom, lower, upper)


def _is_valid_github_numeric_cron(expr: str) -> bool:
    fields = expr.split()
    if len(fields) != 5:
        return False

    for idx, field in enumerate(fields):
        lower, upper = _CRON_FIELD_BOUNDS[idx]
        atoms = field.split(",")
        if not atoms:
            return False
        if not all(_validate_cron_atom(atom, lower, upper) for atom in atoms):
            return False
    return True


def test_workflow_schedule_cron_expressions_are_valid_and_unique_per_workflow() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    invalid: list[str] = []
    duplicates: list[str] = []

    for workflow in workflows:
        payload = _load_yaml(workflow)
        on_block = _workflow_on_block(payload)
        if on_block is None:
            continue
        crons = _extract_schedule_crons(on_block)
        if not crons:
            continue
        checked += len(crons)

        seen: set[str] = set()
        rel = workflow.relative_to(repo_root).as_posix()
        for cron in crons:
            if not _is_valid_github_numeric_cron(cron):
                invalid.append(f"{rel} -> {cron}")
            if cron in seen:
                duplicates.append(f"{rel} -> {cron}")
            seen.add(cron)

    assert checked > 0, "No schedule cron expressions found under .github/workflows"
    assert not invalid, "Invalid workflow schedule cron expression(s):\n" + "\n".join(invalid)
    assert not duplicates, "Duplicate workflow schedule cron expression(s) in same workflow:\n" + "\n".join(
        duplicates
    )
