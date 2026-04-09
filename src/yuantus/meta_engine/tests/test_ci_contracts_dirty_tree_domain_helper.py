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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_dirty_tree_domain_helper_is_documented_and_lists_expected_domains() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_dirty_tree_domain_commands.sh"
    inventory_doc = repo_root / "docs" / "DIRTY_TREE_DOMAIN_INVENTORY_20260409.md"
    delivery_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert inventory_doc.is_file(), f"Missing inventory doc: {inventory_doc}"
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
        "print_dirty_tree_domain_commands.sh",
        "--list-domains",
        "--domain NAME",
        "--status",
        "--git-add-cmd",
        "--commit-plan",
        "subcontracting",
        "docs-parallel",
        "cross-domain-services",
        "strict-gate",
        "migrations",
        "delivery-pack",
    ):
        assert token in help_out, f"help output missing token: {token}"

    list_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--list-domains"],
        text=True,
        capture_output=True,
    )
    assert list_cp.returncode == 0, list_cp.stdout + "\n" + list_cp.stderr
    list_out = list_cp.stdout or ""
    for token in (
        "subcontracting",
        "docs-parallel",
        "cross-domain-services",
        "strict-gate",
        "migrations",
        "delivery-pack",
    ):
        assert token in list_out, f"domain listing missing token: {token}"

    commit_plan_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--domain", "subcontracting", "--commit-plan"],
        text=True,
        capture_output=True,
    )
    assert commit_plan_cp.returncode == 0, commit_plan_cp.stdout + "\n" + commit_plan_cp.stderr
    commit_plan = commit_plan_cp.stdout or ""
    for token in (
        "Suggested branch:",
        "feature/subcontracting-split",
        "Suggested commit title:",
        "feat(subcontracting): split large dirty-tree domain",
        "git add --",
        "src/yuantus/meta_engine/subcontracting",
    ):
        assert token in commit_plan, f"commit-plan output missing token: {token}"

    inventory_text = _read(inventory_doc)
    for token in (
        "print_dirty_tree_domain_commands.sh",
        "--domain subcontracting --status",
        "--domain subcontracting --commit-plan",
    ):
        assert token in inventory_text, f"inventory doc missing token: {token}"

    delivery_text = _read(delivery_index)
    assert "print_dirty_tree_domain_commands.sh" in delivery_text
