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


def test_dirty_tree_residual_closeout_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    closeout = repo_root / "docs" / "DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md"
    branch_closeout = repo_root / "docs" / "BRANCH_CLOSEOUT_SUMMARY_20260409.md"
    reviewer_brief = repo_root / "docs" / "PLM_WORKSPACE_REVIEWER_BRIEF_20260409.md"

    assert closeout.is_file(), f"Missing residual closeout: {closeout}"
    assert branch_closeout.is_file(), f"Missing branch closeout: {branch_closeout}"
    assert reviewer_brief.is_file(), f"Missing reviewer brief: {reviewer_brief}"

    closeout_text = closeout.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Dirty Tree Residual Closeout",
        "503",
        "492",
        "11",
        "ROUTER_SURFACE_MISC_SPLIT_EXECUTION_CARD_20260409.md",
        "SUBCONTRACTING_GOVERNANCE_DOCS_SPLIT_EXECUTION_CARD_20260409.md",
        "PRODUCT_STRATEGY_DOCS_SPLIT_EXECUTION_CARD_20260409.md",
        "Do **not** define a seventh split domain.",
    ):
        assert token in closeout_text, f"residual closeout missing token: {token}"

    branch_text = branch_closeout.read_text(encoding="utf-8", errors="replace")
    assert "DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md" in branch_text

    reviewer_text = reviewer_brief.read_text(encoding="utf-8", errors="replace")
    assert "DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md" in reviewer_text
