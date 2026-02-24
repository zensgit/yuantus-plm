from __future__ import annotations

from pathlib import Path

import yaml

_ALLOWED_SCOPES = {"actions", "contents"}


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


def test_workflow_permissions_scopes_are_allowlisted() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        permissions = payload.get("permissions")
        assert isinstance(permissions, dict), f"{rel} must declare top-level permissions mapping"

        scopes = set(permissions.keys())
        unexpected = sorted(scopes - _ALLOWED_SCOPES)
        assert not unexpected, (
            f"{rel} declares unexpected permissions scopes {unexpected}; "
            f"allowed scopes={sorted(_ALLOWED_SCOPES)}"
        )
