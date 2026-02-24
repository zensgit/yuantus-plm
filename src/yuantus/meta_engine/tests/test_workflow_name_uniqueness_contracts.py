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


def _normalize_workflow_name(raw: str) -> str:
    # Collapse internal whitespace and compare case-insensitively.
    return " ".join(raw.split()).casefold()


def test_workflow_names_are_non_empty_and_unique_case_insensitive() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    seen: dict[str, str] = {}
    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)

        workflow_name = payload.get("name")
        assert isinstance(workflow_name, str), f"{rel} must declare string top-level name"
        normalized = _normalize_workflow_name(workflow_name)
        assert normalized, f"{rel} must declare non-empty top-level name"

        previous = seen.get(normalized)
        assert previous is None, (
            f"{rel} reuses workflow name '{workflow_name}' already used by {previous}; "
            "workflow names must be globally unique (case-insensitive)"
        )
        seen[normalized] = rel
