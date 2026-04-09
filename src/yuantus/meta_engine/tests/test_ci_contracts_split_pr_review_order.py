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


def test_split_pr_review_order_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    order_doc = repo_root / "docs" / "SPLIT_PR_REVIEW_ORDER_20260409.md"
    split_summary = repo_root / "docs" / "SPLIT_BRANCHES_SUMMARY_20260409.md"
    pr155_checklist = repo_root / "docs" / "PR_155_FINAL_REVIEW_CHECKLIST_20260409.md"

    assert order_doc.is_file(), f"Missing review-order doc: {order_doc}"
    assert split_summary.is_file(), f"Missing split summary doc: {split_summary}"
    assert pr155_checklist.is_file(), f"Missing PR #155 checklist: {pr155_checklist}"

    order_text = order_doc.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Split PR Review Order",
        "#155",
        "#156",
        "#157",
        "#158",
        "`#157` and `#158`",
        "do **not** re-bundle the split PRs back into `#155`",
    ):
        assert token in order_text, f"review-order doc missing token: {token}"

    split_text = split_summary.read_text(encoding="utf-8", errors="replace")
    assert "SPLIT_PR_REVIEW_ORDER_20260409.md" in split_text

    checklist_text = pr155_checklist.read_text(encoding="utf-8", errors="replace")
    assert "SPLIT_PR_REVIEW_ORDER_20260409.md" in checklist_text
