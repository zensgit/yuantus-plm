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


def test_subcontracting_first_cut_anchor_helper_exists_and_prints_expected_targets() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_subcontracting_first_cut_anchors.sh"
    execution_card = repo_root / "docs" / "SUBCONTRACTING_SPLIT_EXECUTION_CARD_20260409.md"

    assert script.is_file(), f"Missing script: {script}"
    assert execution_card.is_file(), f"Missing execution card: {execution_card}"

    help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_cp.returncode == 0, help_cp.stdout + "\n" + help_cp.stderr
    help_out = help_cp.stdout or ""
    for token in (
        "Usage:",
        "print_subcontracting_first_cut_anchors.sh",
        "--grep",
        "approval role mapping",
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
        "approval role mapping cleanup cluster",
        "subcontracting/service.py",
        "subcontracting_router.py",
        "test_subcontracting_service.py",
        "test_subcontracting_router.py",
        "git add -p",
    ):
        assert token in default_out, f"default output missing token: {token}"

    grep_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--grep"],
        text=True,
        capture_output=True,
    )
    assert grep_cp.returncode == 0, grep_cp.stdout + "\n" + grep_cp.stderr
    grep_out = grep_cp.stdout or ""
    for token in (
        "rg -n",
        "approval_role_mapping",
        "cleanup_policy",
        "cleanup_history",
        "role_mapping_registry",
    ):
        assert token in grep_out, f"grep output missing token: {token}"

    execution_text = execution_card.read_text(encoding="utf-8", errors="replace")
    for token in (
        "print_subcontracting_first_cut_anchors.sh",
        "--grep",
    ):
        assert token in execution_text, f"execution card missing token: {token}"
