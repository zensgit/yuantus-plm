from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".gitignore").is_file():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .gitignore)")


def test_native_workspace_local_temp_artifacts_are_gitignored() -> None:
    repo_root = _find_repo_root(Path(__file__))
    gitignore = repo_root / ".gitignore"
    assert gitignore.is_file(), f"Missing {gitignore}"

    text = gitignore.read_text(encoding="utf-8", errors="replace")
    for token in (
        ".playwright-cli/",
        ".playwright-mcp/",
        "tmp-plm-workspace-snapshot.md",
    ):
        assert token in text, f".gitignore missing native workspace local-temp token: {token}"
