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


def test_cross_domain_services_split_helper_is_documented_and_prints_expected_commands() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_cross_domain_services_split_helper.sh"
    execution_card = repo_root / "docs" / "CROSS_DOMAIN_SERVICES_SPLIT_EXECUTION_CARD_20260409.md"
    next_step_doc = repo_root / "docs" / "POST_SUBCONTRACTING_NEXT_STEP_20260409.md"

    assert script.is_file(), f"Missing script: {script}"
    assert execution_card.is_file(), f"Missing execution card: {execution_card}"
    assert next_step_doc.is_file(), f"Missing next-step doc: {next_step_doc}"

    help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_cp.returncode == 0, help_cp.stdout + "\n" + help_cp.stderr
    help_out = help_cp.stdout or ""
    for token in (
        "Usage:",
        "print_cross_domain_services_split_helper.sh",
        "--git-add-cmd",
        "--branch-plan",
        "cross-domain-services",
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
        "Cross-domain-services split helper",
        "approvals",
        "document_sync",
        "strict-gate",
        "delivery-pack",
    ):
        assert token in default_out, f"default output missing token: {token}"

    add_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--git-add-cmd"],
        text=True,
        capture_output=True,
    )
    assert add_cp.returncode == 0, add_cp.stdout + "\n" + add_cp.stderr
    add_out = add_cp.stdout or ""
    for token in (
        "git add --",
        "src/yuantus/meta_engine/approvals",
        "src/yuantus/meta_engine/document_sync",
        "migrations/versions/e6f7a8b9c0d1_add_document_sync_site_auth_contract.py",
    ):
        assert token in add_out, f"git-add output missing token: {token}"

    plan_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--branch-plan"],
        text=True,
        capture_output=True,
    )
    assert plan_cp.returncode == 0, plan_cp.stdout + "\n" + plan_cp.stderr
    plan_out = plan_cp.stdout or ""
    for token in (
        "Cross-domain-services branch execution note",
        "feature/cross-domain-followups",
        "feat(meta-engine): split cross-domain service followups",
        "git diff --cached --stat",
        "print_dirty_tree_domain_commands.sh --domain cross-domain-services --status",
    ):
        assert token in plan_out, f"branch-plan output missing token: {token}"

    execution_text = execution_card.read_text(encoding="utf-8", errors="replace")
    for token in (
        "print_cross_domain_services_split_helper.sh",
        "--git-add-cmd",
        "--branch-plan",
        "feature/cross-domain-followups",
    ):
        assert token in execution_text, f"execution card missing token: {token}"

    next_step_text = next_step_doc.read_text(encoding="utf-8", errors="replace")
    for token in (
        "print_cross_domain_services_split_helper.sh",
        "CROSS_DOMAIN_SERVICES_SPLIT_EXECUTION_CARD_20260409.md",
    ):
        assert token in next_step_text, f"next-step doc missing token: {token}"
