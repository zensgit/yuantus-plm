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


def test_pr_155_final_review_checklist_exists_and_links_to_reviewer_path() -> None:
    repo_root = _find_repo_root(Path(__file__))
    checklist = repo_root / "docs" / "PR_155_FINAL_REVIEW_CHECKLIST_20260409.md"
    reviewer_brief = repo_root / "docs" / "PLM_WORKSPACE_REVIEWER_BRIEF_20260409.md"

    assert checklist.is_file(), f"Missing checklist: {checklist}"
    assert reviewer_brief.is_file(), f"Missing reviewer brief: {reviewer_brief}"

    checklist_text = checklist.read_text(encoding="utf-8", errors="replace")
    for token in (
        "PR #155 Final Review Checklist",
        "Must-Review Files",
        "Must-Run Commands",
        "Out-of-Scope",
        "Sign-Off Criteria",
        "src/yuantus/api/app.py",
        "scripts/verify_all.sh",
        "scripts/list_native_workspace_bundle.sh --full --status",
        "docs/DIRTY_TREE_SPLIT_MATRIX_20260409.md",
    ):
        assert token in checklist_text, f"checklist missing token: {token}"

    reviewer_text = reviewer_brief.read_text(encoding="utf-8", errors="replace")
    assert "PR_155_FINAL_REVIEW_CHECKLIST_20260409.md" in reviewer_text
