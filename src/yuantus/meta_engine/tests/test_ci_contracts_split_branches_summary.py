from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def test_split_branches_summary_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    summary = repo_root / "docs" / "SPLIT_BRANCHES_SUMMARY_20260409.md"
    residual_closeout = repo_root / "docs" / "DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md"
    branch_closeout = repo_root / "docs" / "BRANCH_CLOSEOUT_SUMMARY_20260409.md"

    assert summary.is_file(), f"Missing split-branches summary: {summary}"
    assert residual_closeout.is_file(), f"Missing residual closeout: {residual_closeout}"
    assert branch_closeout.is_file(), f"Missing branch closeout: {branch_closeout}"

    summary_text = summary.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Split Branches Summary",
        "feature/router-surface-misc",
        "548a9b3",
        "docs/subcontracting-governance-pack",
        "f1235c8",
        "docs/product-strategy-pack",
        "ffd9398",
        "Do **not** define a seventh split domain.",
    ):
        assert token in summary_text, f"summary missing token: {token}"

    residual_text = residual_closeout.read_text(encoding="utf-8", errors="replace")
    assert "SPLIT_BRANCHES_SUMMARY_20260409.md" in residual_text

    branch_text = branch_closeout.read_text(encoding="utf-8", errors="replace")
    assert "SPLIT_BRANCHES_SUMMARY_20260409.md" in branch_text
