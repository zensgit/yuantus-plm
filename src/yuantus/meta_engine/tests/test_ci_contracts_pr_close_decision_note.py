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


def test_pr_close_decision_note_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    close_note = repo_root / "docs" / "PR_CLOSE_DECISION_NOTE_20260409.md"
    merge_note = repo_root / "docs" / "PR_MERGE_READINESS_NOTE_20260409.md"
    pr155_checklist = repo_root / "docs" / "PR_155_FINAL_REVIEW_CHECKLIST_20260409.md"
    triage = repo_root / "docs" / "PR_TRIAGE_SUMMARY_20260409.md"

    assert close_note.is_file(), f"Missing PR close decision note: {close_note}"
    assert merge_note.is_file(), f"Missing PR merge-readiness note: {merge_note}"
    assert pr155_checklist.is_file(), f"Missing PR #155 checklist: {pr155_checklist}"
    assert triage.is_file(), f"Missing PR triage summary: {triage}"

    close_text = close_note.read_text(encoding="utf-8", errors="replace")
    for token in (
        "PR Close Decision Note",
        "#155",
        "#156",
        "#157",
        "#158",
        "Merge Now If",
        "Hold If",
        "Decision Rule",
        "do **not** wait for `#157` or `#158`",
    ):
        assert token in close_text, f"close decision note missing token: {token}"

    merge_text = merge_note.read_text(encoding="utf-8", errors="replace")
    assert "PR_CLOSE_DECISION_NOTE_20260409.md" in merge_text

    checklist_text = pr155_checklist.read_text(encoding="utf-8", errors="replace")
    assert "PR_CLOSE_DECISION_NOTE_20260409.md" in checklist_text

    triage_text = triage.read_text(encoding="utf-8", errors="replace")
    assert "PR_CLOSE_DECISION_NOTE_20260409.md" in triage_text
