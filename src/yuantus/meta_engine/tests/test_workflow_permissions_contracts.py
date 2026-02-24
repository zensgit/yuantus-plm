from __future__ import annotations

import re
from pathlib import Path

import yaml

_ALLOWED_PERMISSION_VALUES = {"read", "write", "none"}
_TOKEN_ENV_RE = re.compile(r"\b(?:GH_TOKEN|GITHUB_TOKEN):\s*\$\{\{\s*github\.token\s*\}\}")


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


def _raw(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _requires_actions_write(raw_text: str) -> bool:
    # Dispatching/rerunning workflows mutates Actions state and requires actions: write.
    return (
        "gh workflow run" in raw_text
        or "gh run rerun" in raw_text
        or "/actions/workflows/" in raw_text
        and "/dispatches" in raw_text
    )


def _uses_repo_token(raw_text: str) -> bool:
    return bool(_TOKEN_ENV_RE.search(raw_text))


def test_workflow_permissions_follow_contracts() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        raw_text = _raw(workflow)
        payload = _load_yaml(workflow)

        assert "permissions: write-all" not in raw_text, f"{rel} must not use write-all"
        assert "permissions: read-all" not in raw_text, f"{rel} must not use read-all"

        permissions = payload.get("permissions")
        if permissions is not None:
            assert isinstance(permissions, dict), f"{rel} permissions must be a mapping"
            assert "contents" in permissions, f"{rel} permissions must declare contents scope"
            for scope, value in permissions.items():
                assert isinstance(value, str), f"{rel} permission {scope} must be a string"
                assert value in _ALLOWED_PERMISSION_VALUES, (
                    f"{rel} permission {scope} has unsupported value {value!r}; "
                    f"allowed={sorted(_ALLOWED_PERMISSION_VALUES)}"
                )

        if _requires_actions_write(raw_text):
            assert isinstance(permissions, dict), f"{rel} must declare explicit permissions for actions write use"
            assert permissions.get("actions") == "write", (
                f"{rel} requires actions: write (dispatch/rerun), "
                f"got actions={permissions.get('actions')!r}"
            )

        if _uses_repo_token(raw_text):
            assert isinstance(permissions, dict), f"{rel} exposes github.token and must declare permissions"
            assert permissions.get("actions") in {"read", "write"}, (
                f"{rel} exposes github.token and must set actions to read/write"
            )
            assert permissions.get("contents") in {"read", "write"}, (
                f"{rel} exposes github.token and must set contents to read/write"
            )
