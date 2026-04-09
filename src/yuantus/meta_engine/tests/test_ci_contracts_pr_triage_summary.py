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


def test_pr_triage_summary_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    triage = repo_root / "docs" / "PR_TRIAGE_SUMMARY_20260409.md"
    reviewer_brief = repo_root / "docs" / "PLM_WORKSPACE_REVIEWER_BRIEF_20260409.md"
    closeout = repo_root / "docs" / "BRANCH_CLOSEOUT_SUMMARY_20260409.md"
    pr155_checklist = repo_root / "docs" / "PR_155_FINAL_REVIEW_CHECKLIST_20260409.md"

    assert triage.is_file(), f"Missing PR triage summary: {triage}"
    assert reviewer_brief.is_file(), f"Missing reviewer brief: {reviewer_brief}"
    assert closeout.is_file(), f"Missing closeout summary: {closeout}"
    assert pr155_checklist.is_file(), f"Missing PR #155 checklist: {pr155_checklist}"

    triage_text = triage.read_text(encoding="utf-8", errors="replace")
    for token in (
        "PR Triage Summary",
        "#155",
        "#156",
        "#157",
        "#158",
        "Shortest Review Path",
        "Blocking Rule",
        "Suggested Reviewer Routing",
        "do **not** re-bundle `#156`, `#157`, or `#158` back into `#155`",
    ):
        assert token in triage_text, f"triage summary missing token: {token}"

    reviewer_text = reviewer_brief.read_text(encoding="utf-8", errors="replace")
    assert "PR_TRIAGE_SUMMARY_20260409.md" in reviewer_text

    closeout_text = closeout.read_text(encoding="utf-8", errors="replace")
    assert "PR_TRIAGE_SUMMARY_20260409.md" in closeout_text

    checklist_text = pr155_checklist.read_text(encoding="utf-8", errors="replace")
    assert "PR_TRIAGE_SUMMARY_20260409.md" in checklist_text
