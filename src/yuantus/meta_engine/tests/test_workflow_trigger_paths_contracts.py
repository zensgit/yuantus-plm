from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_GLOB_TOKENS = set("*?[]{}!")


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


def _is_glob_pattern(path: str) -> bool:
    return any(ch in path for ch in _GLOB_TOKENS)


def _normalize_literal_path(raw: str) -> str | None:
    path = raw.strip().strip("'\"")
    if not path:
        return None
    if _is_glob_pattern(path):
        return None
    if path.endswith("/"):
        return None
    if path.startswith("!"):
        return None
    if "${{" in path or "}}" in path:
        return None
    return path


def _extract_paths_entries(node: Any) -> list[str]:
    entries: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key) in {"paths", "paths-ignore"} and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        normalized = _normalize_literal_path(item)
                        if normalized:
                            entries.append(normalized)
            entries.extend(_extract_paths_entries(value))
    elif isinstance(node, list):
        for item in node:
            entries.extend(_extract_paths_entries(item))
    return entries


def test_workflow_trigger_literal_paths_exist() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    missing: list[str] = []

    for workflow in workflows:
        payload = _load_yaml(workflow)
        on_block = _workflow_on_block(payload)
        if on_block is None:
            continue

        literal_paths = _extract_paths_entries(on_block)
        for rel in literal_paths:
            checked += 1
            target = repo_root / rel
            if not target.exists():
                missing.append(f"{workflow.relative_to(repo_root).as_posix()} -> {rel}")

    assert checked > 0, "No literal trigger paths found in workflow on.*.paths/paths-ignore"
    assert not missing, "Workflow trigger paths reference missing targets:\n" + "\n".join(missing)
