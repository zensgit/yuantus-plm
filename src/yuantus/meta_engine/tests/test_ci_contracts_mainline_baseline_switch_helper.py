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


def _run_ok(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(  # noqa: S603,S607
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    return cp


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _init_temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo-aware-target"
    repo.mkdir()
    _run_ok(["git", "init"], cwd=repo)
    _run_ok(["git", "config", "user.name", "Codex Test"], cwd=repo)
    _run_ok(["git", "config", "user.email", "codex-test@example.com"], cwd=repo)
    (repo / "README.md").write_text("temp repo\n", encoding="utf-8")
    _run_ok(["git", "add", "README.md"], cwd=repo)
    _run_ok(["git", "commit", "-m", "init"], cwd=repo)
    _run_ok(["git", "branch", "-M", "main"], cwd=repo)
    _run_ok(["git", "switch", "-c", "feature/repo-aware-test"], cwd=repo)
    return repo


def test_mainline_baseline_switch_helper_is_documented_and_prints_expected_commands(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "print_mainline_baseline_switch_commands.sh"
    runbook = repo_root / "docs" / "RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md"
    repo_readme = repo_root / "README.md"
    delivery_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert script.is_file(), f"Missing script: {script}"
    assert runbook.is_file(), f"Missing runbook: {runbook}"
    assert repo_readme.is_file(), f"Missing README: {repo_readme}"
    assert delivery_index.is_file(), f"Missing delivery index: {delivery_index}"

    help_out = _run_ok(["bash", str(script), "--help"]).stdout or ""
    for token in (
        "Usage:",
        "print_mainline_baseline_switch_commands.sh",
        "--repo PATH",
        "--worktree-branch NAME",
        "--topic-branch NAME",
        "--backup-branch NAME",
    ):
        assert token in help_out, f"help output missing token: {token}"

    default_out = _run_ok(["bash", str(script)]).stdout or ""
    for token in (
        "Mainline baseline switch templates",
        "## 1) Inspect current state",
        "stash push -u -m 'baseline-switch ",
        "worktree add -b baseline/mainline-",
        "git -C <worktree-path> switch -c feature/<topic>-<YYYYMMDD>",
        "## 5) Recommended: publish the topic branch so the clean worktree is recoverable",
        "git -C <worktree-path> push -u origin feature/<topic>-<YYYYMMDD>",
        "## 8) Rollback / recovery references",
    ):
        assert token in default_out, f"default output missing token: {token}"

    target_repo = _init_temp_repo(tmp_path)
    worktree_parent = target_repo.parent / f"{target_repo.name}-worktrees"
    worktree_path = worktree_parent / "mainline-test"
    custom_out = _run_ok(
        [
            "bash",
            str(script),
            "--repo",
            str(target_repo),
            "--worktree-name",
            "mainline-test",
            "--topic-branch",
            "feature/mainline-test-20260419",
        ]
    ).stdout or ""

    for token in (
        f"# repo: {target_repo}",
        "# current branch: feature/repo-aware-test",
        "# suggested backup branch: backup/feature-repo-aware-test-",
        f"# suggested worktree: {worktree_path}",
        "# suggested worktree branch: baseline/mainline-test",
        "# suggested topic branch: feature/mainline-test-20260419",
        f"git -C {target_repo} rev-list --left-right --count feature/repo-aware-test...origin/main",
        f"git -C {target_repo} branch backup/feature-repo-aware-test-",
        f"mkdir -p {worktree_parent}",
        f"git -C {target_repo} worktree add -b baseline/mainline-test {worktree_path} origin/main",
        f"git -C {worktree_path} switch -c feature/mainline-test-20260419",
        f"git -C {worktree_path} push -u origin feature/mainline-test-20260419",
    ):
        assert token in custom_out, f"custom output missing token: {token}"

    runbook_text = _read(runbook)
    for token in (
        "print_mainline_baseline_switch_commands.sh",
        "--topic-branch",
        "baseline/mainline-<stamp>",
        "git -C ../Yuantus-worktrees/mainline-<stamp> switch -c feature/<topic>-<YYYYMMDD>",
        "git -C ../Yuantus-worktrees/mainline-<stamp> push -u origin feature/<topic>-<YYYYMMDD>",
    ):
        assert token in runbook_text, f"runbook missing token: {token}"

    readme_text = _read(repo_readme)
    for token in (
        "RUNBOOK_MAINLINE_BASELINE_SWITCH_20260414.md",
        "Mainline baseline switch",
    ):
        assert token in readme_text, f"README missing token: {token}"

    delivery_index_text = _read(delivery_index)
    for token in (
        "print_mainline_baseline_switch_commands.sh",
        "prints safe command templates for preserving a dirty feature worktree",
    ):
        assert token in delivery_index_text, f"DELIVERY_SCRIPTS_INDEX missing token: {token}"
