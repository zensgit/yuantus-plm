from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_SHA_REF_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_VERSION_REF_RE = re.compile(r"^v\d+(?:\.\d+){0,2}$")
_FORBIDDEN_REFS = {"main", "master", "latest", "head"}


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


def _extract_uses_entries(node: Any) -> list[str]:
    entries: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key) == "uses" and isinstance(value, str):
                entries.append(value.strip())
            entries.extend(_extract_uses_entries(value))
    elif isinstance(node, list):
        for item in node:
            entries.extend(_extract_uses_entries(item))
    return entries


def _is_allowed_uses_ref(uses: str) -> bool:
    if uses.startswith("./"):
        return True
    if uses.startswith("docker://"):
        return True

    if "@" not in uses:
        return False
    _, ref = uses.rsplit("@", 1)
    if not ref:
        return False
    if ref.lower() in _FORBIDDEN_REFS:
        return False
    return bool(_SHA_REF_RE.fullmatch(ref) or _VERSION_REF_RE.fullmatch(ref))


def test_workflow_uses_entries_are_pinned_to_version_or_sha() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    checked = 0
    invalid: list[str] = []

    for workflow in workflows:
        payload = _load_yaml(workflow)
        uses_entries = _extract_uses_entries(payload)
        rel = workflow.relative_to(repo_root).as_posix()
        for uses in uses_entries:
            checked += 1
            if not _is_allowed_uses_ref(uses):
                invalid.append(f"{rel} -> {uses}")

    assert checked > 0, "No workflow uses entries discovered under .github/workflows"
    assert not invalid, (
        "Workflow uses entries must be pinned to version tags (vX[/vX.Y/vX.Y.Z]) or commit SHA:\n"
        + "\n".join(invalid)
    )
