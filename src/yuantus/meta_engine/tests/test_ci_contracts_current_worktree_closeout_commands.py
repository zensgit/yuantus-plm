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


def test_current_worktree_closeout_helper_is_documented_and_prints_expected_groups() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_current_worktree_closeout_commands.sh"
    closeout_doc = repo_root / "docs" / "DEV_AND_VERIFICATION_CURRENT_WORKTREE_PR_SPLIT_COMMANDS_20260425.md"
    scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert closeout_doc.is_file(), f"Missing closeout doc: {closeout_doc}"

    help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_cp.returncode == 0, help_cp.stdout + "\n" + help_cp.stderr
    help_out = help_cp.stdout or ""
    for token in (
        "Usage:",
        "print_current_worktree_closeout_commands.sh",
        "--commands",
        "--group NAME",
        "current worktree closeout split plan",
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
        "Current worktree closeout split plan:",
        "1. closeout-docs-and-index",
        "2. closeout-tooling",
        "3. odoo18-verifier-hardening",
        "4. router-decomposition-portfolio",
        "Local-only exclusions:",
        ".claude/",
        "local-dev-env/",
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
        "git diff --stat -- docs/DELIVERY_DOC_INDEX.md",
        "git add -- docs/DELIVERY_DOC_INDEX.md",
        "scripts/verify_odoo18_plm_stack.sh",
        "src/yuantus/api/app.py",
        "Never stage local-only artifacts:",
    ):
        assert token in commands_out, f"commands output missing token: {token}"

    for forbidden_stage in ("git add -- .claude", "git add -- local-dev-env"):
        assert forbidden_stage not in commands_out
    assert "git add -- src/yuantus/api/app.py src/yuantus/meta_engine/web" not in commands_out
    assert "src/yuantus/meta_engine/web src/yuantus/meta_engine/tests" not in commands_out

    group_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--group", "odoo18-verifier-hardening"],
        text=True,
        capture_output=True,
    )
    assert group_cp.returncode == 0, group_cp.stdout + "\n" + group_cp.stderr
    group_out = group_cp.stdout or ""
    assert "3. odoo18-verifier-hardening" in group_out
    assert "closeout-docs-and-index" not in group_out
    assert "router-decomposition-portfolio" not in group_out

    group_commands_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--group", "closeout-docs-and-index", "--commands"],
        text=True,
        capture_output=True,
    )
    assert group_commands_cp.returncode == 0, group_commands_cp.stdout + "\n" + group_commands_cp.stderr
    group_commands_out = group_commands_cp.stdout or ""
    assert "1. closeout-docs-and-index" in group_commands_out
    assert "git add -- docs/DELIVERY_DOC_INDEX.md" in group_commands_out
    assert "scripts/verify_odoo18_plm_stack.sh" not in group_commands_out
    assert "Never stage local-only artifacts:" in group_commands_out

    tooling_commands_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--group", "closeout-tooling", "--commands"],
        text=True,
        capture_output=True,
    )
    assert tooling_commands_cp.returncode == 0, tooling_commands_cp.stdout + "\n" + tooling_commands_cp.stderr
    tooling_commands_out = tooling_commands_cp.stdout or ""
    assert "2. closeout-tooling" in tooling_commands_out
    assert "print_current_worktree_closeout_commands.sh" in tooling_commands_out
    assert "docs/DELIVERY_SCRIPTS_INDEX_20260202.md" in tooling_commands_out
    assert "test_ci_contracts_current_worktree_closeout_commands.py" in tooling_commands_out
    assert "DEV_AND_VERIFICATION_CURRENT_WORKTREE_CLOSEOUT_TOOLING_GROUP_20260425" in tooling_commands_out
    assert "scripts/verify_odoo18_plm_stack.sh" not in tooling_commands_out
    assert "src/yuantus/api/app.py" not in tooling_commands_out

    router_commands_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--group", "router-decomposition-portfolio", "--commands"],
        text=True,
        capture_output=True,
    )
    assert router_commands_cp.returncode == 0, router_commands_cp.stdout + "\n" + router_commands_cp.stderr
    router_commands_out = router_commands_cp.stdout or ""
    for token in (
        "':(glob)src/yuantus/meta_engine/web/report*_router.py'",
        "':(glob)src/yuantus/meta_engine/tests/test_report*_router*.py'",
        "src/yuantus/meta_engine/web/quality_common.py",
        "src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py",
    ):
        assert token in router_commands_out
    assert "git add -- src/yuantus/api/app.py src/yuantus/meta_engine/web" not in router_commands_out
    assert "src/yuantus/meta_engine/tests docs/DEV_AND_VERIFICATION" not in router_commands_out

    invalid_group_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--group", "unknown"],
        text=True,
        capture_output=True,
    )
    assert invalid_group_cp.returncode == 2
    assert "unsupported group: unknown" in invalid_group_cp.stderr

    closeout_text = closeout_doc.read_text(encoding="utf-8", errors="replace")
    scripts_index_text = scripts_index.read_text(encoding="utf-8", errors="replace")
    for token in (
        "closeout-docs-and-index",
        "closeout-tooling",
        "odoo18-verifier-hardening",
        "router-decomposition-portfolio",
        "print_current_worktree_closeout_commands.sh",
    ):
        assert token in closeout_text
    assert "print_current_worktree_closeout_commands.sh" in scripts_index_text
