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


def test_claude_code_parallel_helper_is_documented_and_runnable() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_claude_code_parallel_commands.sh"
    reviewer_script = repo_root / "scripts" / "run_claude_code_parallel_reviewer.sh"
    runbook = repo_root / "docs" / "RUNBOOK_CLAUDE_CODE_PARALLEL_WORKTREE.md"
    repo_readme = repo_root / "README.md"
    verification_doc = repo_root / "docs" / "VERIFICATION.md"
    delivery_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert reviewer_script.is_file(), f"Missing reviewer script: {reviewer_script}"
    assert runbook.is_file(), f"Missing runbook: {runbook}"
    assert repo_readme.is_file(), f"Missing README: {repo_readme}"
    assert verification_doc.is_file(), f"Missing verification doc: {verification_doc}"
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
        "print_claude_code_parallel_commands.sh",
        "--mode MODE",
        "--worktree-name NAME",
        "read-only",
        "worktree",
        "reviewer",
    ):
        assert token in help_out, f"help output missing token: {token}"

    worktree_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--mode", "worktree", "--worktree-name", "claude-test-scope"],
        text=True,
        capture_output=True,
    )
    assert worktree_cp.returncode == 0, worktree_cp.stdout + "\n" + worktree_cp.stderr
    worktree_out = worktree_cp.stdout or ""
    for token in (
        "claude auth status",
        "Requires explicit user authorization before running.",
        "claude --worktree claude-test-scope",
        "Stay within one narrow scope",
        "do not use permission-skipping modes",
        "do not commit .claude/ or local-dev-env/",
    ):
        assert token in worktree_out, f"worktree output missing token: {token}"

    read_only_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--mode", "read-only"],
        text=True,
        capture_output=True,
    )
    assert read_only_cp.returncode == 0, read_only_cp.stdout + "\n" + read_only_cp.stderr
    read_only_out = read_only_cp.stdout or ""
    for token in (
        "printf '%s\\n'",
        "claude -p --no-session-persistence --tools \"\"",
        "Treat output as advisory only",
        "do not authorize implementation, merge, phase transition, production cutover, or evidence signoff",
    ):
        assert token in read_only_out, f"read-only output missing token: {token}"
    assert "claude -p --add-dir" not in read_only_out

    reviewer_help_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(reviewer_script), "--help"],
        text=True,
        capture_output=True,
    )
    assert reviewer_help_cp.returncode == 0, reviewer_help_cp.stdout + "\n" + reviewer_help_cp.stderr
    reviewer_help = reviewer_help_cp.stdout or ""
    for token in (
        "Usage:",
        "run_claude_code_parallel_reviewer.sh",
        "--repo PATH",
        "--branch NAME",
        "--out PATH",
        "--prompt TEXT",
    ):
        assert token in reviewer_help, f"reviewer help missing token: {token}"

    reviewer_template_cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--mode", "reviewer"],
        text=True,
        capture_output=True,
    )
    assert reviewer_template_cp.returncode == 0, (
        reviewer_template_cp.stdout + "\n" + reviewer_template_cp.stderr
    )
    reviewer_template = reviewer_template_cp.stdout or ""
    assert "claude -p --no-session-persistence --tools \"\"" in reviewer_template
    assert "Treat output as advisory only" in reviewer_template
    assert "claude -p --add-dir" not in reviewer_template

    reviewer_script_text = _read(reviewer_script)
    for token in (
        "Treat output as advisory only",
        "do not authorize implementation, merge, phase transition, production cutover, or evidence signoff",
        "printf '%s\\n' \"${PROMPT}\" | claude -p --no-session-persistence --tools \"\"",
    ):
        assert token in reviewer_script_text, f"reviewer script missing token: {token}"
    assert "claude -p --add-dir" not in reviewer_script_text

    expected_tokens = {
        repo_readme: (
            "print_claude_code_parallel_commands.sh",
            "run_claude_code_parallel_reviewer.sh",
            "RUNBOOK_CLAUDE_CODE_PARALLEL_WORKTREE.md",
        ),
        verification_doc: (
            "print_claude_code_parallel_commands.sh",
            "run_claude_code_parallel_reviewer.sh",
            "RUNBOOK_CLAUDE_CODE_PARALLEL_WORKTREE.md",
        ),
        runbook: (
            "print_claude_code_parallel_commands.sh",
            "run_claude_code_parallel_reviewer.sh",
            "claude --worktree",
            "claude auth status",
        ),
        delivery_index: (
            "print_claude_code_parallel_commands.sh",
            "run_claude_code_parallel_reviewer.sh",
        ),
    }

    for path, tokens in expected_tokens.items():
        text = _read(path)
        for token in tokens:
            assert token in text, f"{path} missing token: {token}"
