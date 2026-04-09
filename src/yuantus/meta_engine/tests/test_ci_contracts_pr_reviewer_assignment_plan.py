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


def test_pr_reviewer_assignment_plan_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    assignment = repo_root / "docs" / "PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md"
    triage = repo_root / "docs" / "PR_TRIAGE_SUMMARY_20260409.md"
    reviewer_brief = repo_root / "docs" / "PLM_WORKSPACE_REVIEWER_BRIEF_20260409.md"
    pr155_checklist = repo_root / "docs" / "PR_155_FINAL_REVIEW_CHECKLIST_20260409.md"

    assert assignment.is_file(), f"Missing reviewer assignment plan: {assignment}"
    assert triage.is_file(), f"Missing PR triage summary: {triage}"
    assert reviewer_brief.is_file(), f"Missing reviewer brief: {reviewer_brief}"
    assert pr155_checklist.is_file(), f"Missing PR #155 checklist: {pr155_checklist}"

    assignment_text = assignment.read_text(encoding="utf-8", errors="replace")
    for token in (
        "PR Reviewer Assignment Plan",
        "there is no checked-in `CODEOWNERS` file",
        "#155",
        "#156",
        "#157",
        "#158",
        "Suggested Reviewer Lanes",
        "Mention Plan",
        "Fallback If Only One Reviewer Is Available",
    ):
        assert token in assignment_text, f"assignment plan missing token: {token}"

    triage_text = triage.read_text(encoding="utf-8", errors="replace")
    assert "PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md" in triage_text

    reviewer_text = reviewer_brief.read_text(encoding="utf-8", errors="replace")
    assert "PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md" in reviewer_text

    checklist_text = pr155_checklist.read_text(encoding="utf-8", errors="replace")
    assert "PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md" in checklist_text
