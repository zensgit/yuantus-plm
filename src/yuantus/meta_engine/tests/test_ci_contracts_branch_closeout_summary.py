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


def test_branch_closeout_summary_exists_and_is_linked_from_reviewer_brief() -> None:
    repo_root = _find_repo_root(Path(__file__))
    summary = repo_root / "docs" / "BRANCH_CLOSEOUT_SUMMARY_20260409.md"
    reviewer_brief = repo_root / "docs" / "PLM_WORKSPACE_REVIEWER_BRIEF_20260409.md"

    assert summary.is_file(), f"Missing summary: {summary}"
    assert reviewer_brief.is_file(), f"Missing reviewer brief: {reviewer_brief}"

    summary_text = summary.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Branch Closeout Summary",
        "feature/claude-c43-cutted-parts-throughput",
        "PR: `zensgit/yuantus-plm#155`",
        "Landed Scope",
        "Verification",
        "Reviewer Entrypoints",
        "Dirty-Tree Split Safety",
        "Next Actions",
        "docs/PR_155_FINAL_REVIEW_CHECKLIST_20260409.md",
        "docs/DIRTY_TREE_SPLIT_MATRIX_20260409.md",
    ):
        assert token in summary_text, f"summary missing token: {token}"

    reviewer_text = reviewer_brief.read_text(encoding="utf-8", errors="replace")
    assert "BRANCH_CLOSEOUT_SUMMARY_20260409.md" in reviewer_text
