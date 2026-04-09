from __future__ import annotations

import subprocess
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


def test_dirty_tree_domain_coverage_helper_is_documented_and_runs() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_dirty_tree_domain_coverage.sh"
    coverage_doc = repo_root / "docs" / "DIRTY_TREE_DOMAIN_COVERAGE_20260409.md"
    matrix_doc = repo_root / "docs" / "DIRTY_TREE_SPLIT_MATRIX_20260409.md"
    delivery_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert coverage_doc.is_file(), f"Missing coverage doc: {coverage_doc}"
    assert matrix_doc.is_file(), f"Missing split matrix doc: {matrix_doc}"
    assert delivery_index.is_file(), f"Missing delivery index: {delivery_index}"

    help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_cp.returncode == 0, help_cp.stdout + "\n" + help_cp.stderr
    help_out = help_cp.stdout or ""
    for token in (
        "Usage:",
        "print_dirty_tree_domain_coverage.sh",
        "--summary",
        "--by-domain",
        "--unassigned",
        "Same as --summary.",
    ):
        assert token in help_out, f"help output missing token: {token}"

    summary_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script)],
        text=True,
        capture_output=True,
    )
    assert summary_cp.returncode == 0, summary_cp.stdout + "\n" + summary_cp.stderr
    summary_out = summary_cp.stdout or ""
    for token in (
        "Dirty-tree domain coverage summary:",
        "total dirty paths:",
        "assigned dirty paths:",
        "unassigned dirty paths:",
        "coverage gap present:",
    ):
        assert token in summary_out, f"summary output missing token: {token}"

    by_domain_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--by-domain"],
        text=True,
        capture_output=True,
    )
    assert by_domain_cp.returncode == 0, by_domain_cp.stdout + "\n" + by_domain_cp.stderr
    by_domain_out = by_domain_cp.stdout or ""
    for token in (
        "subcontracting",
        "docs-parallel",
        "cross-domain-services",
        "migrations",
        "strict-gate",
        "delivery-pack",
    ):
        assert token in by_domain_out, f"by-domain output missing token: {token}"

    unassigned_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--unassigned"],
        text=True,
        capture_output=True,
    )
    assert unassigned_cp.returncode == 0, unassigned_cp.stdout + "\n" + unassigned_cp.stderr
    assert (unassigned_cp.stdout or "").strip(), "unassigned output should not be empty"

    coverage_text = coverage_doc.read_text(encoding="utf-8", errors="replace")
    for token in (
        "504",
        "492",
        "12",
        "router-surface-misc",
        "subcontracting-governance-docs",
        "product-strategy-docs",
        "dirty-tree-tooling",
        "print_dirty_tree_domain_coverage.sh --unassigned",
        "Do not create a seventh cleanup domain yet.",
    ):
        assert token in coverage_text, f"coverage doc missing token: {token}"

    matrix_text = matrix_doc.read_text(encoding="utf-8", errors="replace")
    for token in (
        "print_dirty_tree_domain_coverage.sh",
        "DIRTY_TREE_DOMAIN_COVERAGE_20260409.md",
        "Coverage Check",
    ):
        assert token in matrix_text, f"matrix doc missing token: {token}"

    delivery_text = delivery_index.read_text(encoding="utf-8", errors="replace")
    assert "print_dirty_tree_domain_coverage.sh" in delivery_text
