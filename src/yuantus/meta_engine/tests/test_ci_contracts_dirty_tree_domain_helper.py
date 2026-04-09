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
    split_order_doc = repo_root / "docs" / "DIRTY_TREE_SPLIT_ORDER_20260409.md"
    next_step_doc = repo_root / "docs" / "POST_SUBCONTRACTING_NEXT_STEP_20260409.md"
    delivery_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert inventory_doc.is_file(), f"Missing inventory doc: {inventory_doc}"
    assert split_order_doc.is_file(), f"Missing split-order doc: {split_order_doc}"
    assert next_step_doc.is_file(), f"Missing next-step doc: {next_step_doc}"
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
        "--recommended-order",
        "--first-step",
        "--after-first-cut",
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

    order_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--recommended-order"],
        text=True,
        capture_output=True,
    )
    assert order_cp.returncode == 0, order_cp.stdout + "\n" + order_cp.stderr
    order_out = order_cp.stdout or ""
    for token in (
        "1. subcontracting",
        "2. docs-parallel",
        "3. cross-domain-services",
        "4. migrations",
        "5. strict-gate",
        "6. delivery-pack",
    ):
        assert token in order_out, f"recommended-order output missing token: {token}"

    first_step_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--first-step"],
        text=True,
        capture_output=True,
    )
    assert first_step_cp.returncode == 0, first_step_cp.stdout + "\n" + first_step_cp.stderr
    first_step_out = first_step_cp.stdout or ""
    for token in (
        "Recommended first split domain:",
        "subcontracting",
        "feature/subcontracting-split",
        "--domain subcontracting --status",
        "--domain subcontracting --commit-plan",
        "approval role mapping cleanup cluster",
    ):
        assert token in first_step_out, f"first-step output missing token: {token}"

    after_first_cut_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--after-first-cut"],
        text=True,
        capture_output=True,
    )
    assert after_first_cut_cp.returncode == 0, after_first_cut_cp.stdout + "\n" + after_first_cut_cp.stderr
    after_first_cut_out = after_first_cut_cp.stdout or ""
    for token in (
        "Recommended next split domain after the subcontracting first cut:",
        "docs-parallel",
        "--domain docs-parallel --status",
        "--domain docs-parallel --commit-plan",
        "cross-domain-services",
    ):
        assert token in after_first_cut_out, f"after-first-cut output missing token: {token}"

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
        "--recommended-order",
        "--first-step",
        "--after-first-cut",
        "--domain subcontracting --status",
        "--domain subcontracting --commit-plan",
        "DIRTY_TREE_SPLIT_ORDER_20260409.md",
        "SUBCONTRACTING_SPLIT_EXECUTION_CARD_20260409.md",
    ):
        assert token in inventory_text, f"inventory doc missing token: {token}"

    split_order_text = _read(split_order_doc)
    for token in (
        "--after-first-cut",
        "POST_SUBCONTRACTING_NEXT_STEP_20260409.md",
        "docs-parallel",
        "cross-domain-services",
    ):
        assert token in split_order_text, f"split-order doc missing token: {token}"

    next_step_text = _read(next_step_doc)
    for token in (
        "docs-parallel",
        "cross-domain-services",
        "--after-first-cut",
        "--domain docs-parallel --status",
        "--domain cross-domain-services --commit-plan",
    ):
        assert token in next_step_text, f"next-step doc missing token: {token}"

    delivery_text = _read(delivery_index)
    assert "print_dirty_tree_domain_commands.sh" in delivery_text
