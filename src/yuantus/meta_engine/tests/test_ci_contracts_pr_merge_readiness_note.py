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


def test_pr_merge_readiness_note_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    readiness = repo_root / "docs" / "PR_MERGE_READINESS_NOTE_20260409.md"
    triage = repo_root / "docs" / "PR_TRIAGE_SUMMARY_20260409.md"
    assignment = repo_root / "docs" / "PR_REVIEWER_ASSIGNMENT_PLAN_20260409.md"
    pr155_checklist = repo_root / "docs" / "PR_155_FINAL_REVIEW_CHECKLIST_20260409.md"

    assert readiness.is_file(), f"Missing merge-readiness note: {readiness}"
    assert triage.is_file(), f"Missing PR triage summary: {triage}"
    assert assignment.is_file(), f"Missing reviewer assignment plan: {assignment}"
    assert pr155_checklist.is_file(), f"Missing PR #155 checklist: {pr155_checklist}"

    readiness_text = readiness.read_text(encoding="utf-8", errors="replace")
    for token in (
        "PR Merge Readiness Note",
        "#155",
        "#156",
        "#157",
        "#158",
        "Merge Order",
        "Merge Checks",
        "Non-Blocking Rule",
        "do **not** re-bundle the split PRs back into `#155`",
    ):
        assert token in readiness_text, f"merge-readiness note missing token: {token}"

    triage_text = triage.read_text(encoding="utf-8", errors="replace")
    assert "PR_MERGE_READINESS_NOTE_20260409.md" in triage_text

    assignment_text = assignment.read_text(encoding="utf-8", errors="replace")
    assert "PR_MERGE_READINESS_NOTE_20260409.md" in assignment_text

    checklist_text = pr155_checklist.read_text(encoding="utf-8", errors="replace")
    assert "PR_MERGE_READINESS_NOTE_20260409.md" in checklist_text
