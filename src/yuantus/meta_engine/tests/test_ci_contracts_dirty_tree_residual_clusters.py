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


def test_dirty_tree_residual_clusters_note_is_linked_from_coverage_and_closeout() -> None:
    repo_root = _find_repo_root(Path(__file__))
    note = repo_root / "docs" / "DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md"
    coverage = repo_root / "docs" / "DIRTY_TREE_DOMAIN_COVERAGE_20260409.md"
    matrix = repo_root / "docs" / "DIRTY_TREE_SPLIT_MATRIX_20260409.md"
    closeout = repo_root / "docs" / "BRANCH_CLOSEOUT_SUMMARY_20260409.md"

    assert note.is_file(), f"Missing note: {note}"
    assert coverage.is_file(), f"Missing coverage doc: {coverage}"
    assert matrix.is_file(), f"Missing matrix doc: {matrix}"
    assert closeout.is_file(), f"Missing closeout summary: {closeout}"

    note_text = note.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Dirty Tree Residual Clusters",
        "feature/claude-c43-cutted-parts-throughput",
        "503",
        "492",
        "11",
        "router-surface-misc",
        "subcontracting-governance-docs",
        "product-strategy-docs",
        "Do **not** define a seventh split domain yet.",
        "print_dirty_tree_domain_coverage.sh --unassigned",
    ):
        assert token in note_text, f"residual note missing token: {token}"

    coverage_text = coverage.read_text(encoding="utf-8", errors="replace")
    assert "DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md" in coverage_text

    matrix_text = matrix.read_text(encoding="utf-8", errors="replace")
    assert "DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md" in matrix_text

    closeout_text = closeout.read_text(encoding="utf-8", errors="replace")
    assert "DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md" in closeout_text
