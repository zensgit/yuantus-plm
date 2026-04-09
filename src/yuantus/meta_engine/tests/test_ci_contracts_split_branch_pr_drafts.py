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


def test_split_branch_pr_drafts_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    drafts = repo_root / "docs" / "SPLIT_BRANCH_PR_DRAFTS_20260409.md"
    summary = repo_root / "docs" / "SPLIT_BRANCHES_SUMMARY_20260409.md"
    residual_closeout = repo_root / "docs" / "DIRTY_TREE_RESIDUAL_CLOSEOUT_20260409.md"

    assert drafts.is_file(), f"Missing PR drafts doc: {drafts}"
    assert summary.is_file(), f"Missing split summary doc: {summary}"
    assert residual_closeout.is_file(), f"Missing residual closeout doc: {residual_closeout}"

    text = drafts.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Split Branch PR Drafts",
        "feature/router-surface-misc",
        "548a9b3",
        "docs/subcontracting-governance-pack",
        "f1235c8",
        "docs/product-strategy-pack",
        "ffd9398",
        "suggested title:",
        "Suggested body:",
        "pytest src/yuantus/meta_engine/tests/test_box_router.py",
    ):
        assert token in text, f"drafts doc missing token: {token}"

    summary_text = summary.read_text(encoding="utf-8", errors="replace")
    assert "SPLIT_BRANCH_PR_DRAFTS_20260409.md" in summary_text

    closeout_text = residual_closeout.read_text(encoding="utf-8", errors="replace")
    assert "SPLIT_BRANCH_PR_DRAFTS_20260409.md" in closeout_text
