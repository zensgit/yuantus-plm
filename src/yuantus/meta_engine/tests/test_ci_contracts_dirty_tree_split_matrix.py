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


def test_dirty_tree_split_matrix_is_documented_and_prints_expected_entries() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_dirty_tree_split_matrix.sh"
    matrix_doc = repo_root / "docs" / "DIRTY_TREE_SPLIT_MATRIX_20260409.md"

    assert script.is_file(), f"Missing script: {script}"
    assert matrix_doc.is_file(), f"Missing matrix doc: {matrix_doc}"

    help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_cp.returncode == 0, help_cp.stdout + "\n" + help_cp.stderr
    help_out = help_cp.stdout or ""
    for token in (
        "Usage:",
        "print_dirty_tree_split_matrix.sh",
        "--commands",
        "dirty-tree split matrix",
    ):
        assert token in help_out, f"help output missing token: {token}"

    default_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script)],
        text=True,
        capture_output=True,
    )
    assert default_cp.returncode == 0, default_cp.stdout + "\n" + default_cp.stderr
    default_out = default_cp.stdout or ""
    for token in (
        "Dirty-tree split matrix:",
        "1. subcontracting",
        "2. docs-parallel",
        "3. cross-domain-services",
        "4. migrations",
        "5. strict-gate",
        "6. delivery-pack",
        "feature/subcontracting-split",
        "docs/delivery-pack-followup",
    ):
        assert token in default_out, f"default output missing token: {token}"

    commands_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--commands"],
        text=True,
        capture_output=True,
    )
    assert commands_cp.returncode == 0, commands_cp.stdout + "\n" + commands_cp.stderr
    commands_out = commands_cp.stdout or ""
    for token in (
        "print_subcontracting_first_cut_anchors.sh --branch-plan",
        "print_docs_parallel_split_helper.sh --branch-plan",
        "print_cross_domain_services_split_helper.sh --branch-plan",
        "print_dirty_tree_domain_commands.sh --domain migrations --commit-plan",
        "print_strict_gate_split_helper.sh --branch-plan",
        "print_delivery_pack_split_helper.sh --branch-plan",
    ):
        assert token in commands_out, f"commands output missing token: {token}"

    matrix_text = matrix_doc.read_text(encoding="utf-8", errors="replace")
    for token in (
        "feature/subcontracting-split",
        "docs/parallel-artifact-pack",
        "feature/cross-domain-followups",
        "feature/domain-migrations-followup",
        "chore/strict-gate-followups",
        "docs/delivery-pack-followup",
        "print_dirty_tree_split_matrix.sh",
    ):
        assert token in matrix_text, f"matrix doc missing token: {token}"
