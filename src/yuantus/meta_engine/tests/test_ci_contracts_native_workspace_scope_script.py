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


def test_native_workspace_scope_script_has_help_and_declares_bundle_files() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "list_native_workspace_bundle.sh"
    assert script.is_file(), f"Missing {script}"

    text = _read(script)
    for token in (
        "Usage:",
        "scripts/list_native_workspace_bundle.sh [--full] [--status] [--git-add-cmd] [--commit-plan]",
        "--full",
        "git status --short --",
        "--git-add-cmd",
        "--commit-plan",
        "src/yuantus/api/routers/plm_workspace.py",
        "src/yuantus/api/routers/workbench.py",
        "src/yuantus/web/plm_workspace.html",
        "src/yuantus/web/workbench.html",
        "src/yuantus/api/tests/test_plm_workspace_router.py",
        "src/yuantus/api/tests/test_workbench_router.py",
        "playwright/tests/plm_workspace_documents_ui.spec.js",
        "playwright/tests/plm_workspace_demo_resume.spec.js",
        "playwright/tests/plm_workspace_document_handoff.spec.js",
        "playwright/tests/plm_workspace_eco_actions.spec.js",
        "scripts/list_native_workspace_bundle.sh",
        "scripts/verify_playwright_plm_workspace_all.sh",
        "scripts/verify_playwright_plm_workspace_eco_actions.sh",
    ):
        assert token in text, f"list_native_workspace_bundle.sh missing token: {token}"

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""
    for token in (
        "Usage:",
        "--full",
        "--status",
        "--git-add-cmd",
        "--commit-plan",
        "native PLM workspace",
        "bundle scope",
    ):
        assert token in out, f"list_native_workspace_bundle.sh help missing token: {token}"


def test_native_workspace_scope_script_prints_expected_anchor_paths() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "list_native_workspace_bundle.sh"
    assert script.is_file(), f"Missing {script}"

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        text=True,
        capture_output=True,
        cwd=repo_root,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    lines = [line.strip() for line in (cp.stdout or "").splitlines() if line.strip()]
    for token in (
        "src/yuantus/api/routers/plm_workspace.py",
        "src/yuantus/web/plm_workspace.html",
        "src/yuantus/api/tests/test_plm_workspace_router.py",
        "src/yuantus/api/tests/test_workbench_router.py",
        "playwright/tests/README_plm_workspace.md",
        "scripts/list_native_workspace_bundle.sh",
        "scripts/verify_playwright_plm_workspace_all.sh",
        "scripts/verify_playwright_plm_workspace_eco_actions.sh",
        "src/yuantus/meta_engine/tests/test_ci_contracts_native_workspace_bundle_scope.py",
    ):
        assert token in lines, f"list_native_workspace_bundle.sh output missing: {token}"


def test_native_workspace_scope_script_full_mode_includes_tracked_harness_entrypoints() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "list_native_workspace_bundle.sh"
    assert script.is_file(), f"Missing {script}"

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script), "--full"],
        text=True,
        capture_output=True,
        cwd=repo_root,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    lines = [line.strip() for line in (cp.stdout or "").splitlines() if line.strip()]
    for token in (
        "README.md",
        "docs/VERIFICATION.md",
        "docs/DELIVERY_SCRIPTS_INDEX_20260202.md",
        "package.json",
        "scripts/verify_all.sh",
        "src/yuantus/api/app.py",
        "src/yuantus/api/middleware/auth_enforce.py",
        "src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py",
    ):
        assert token in lines, f"list_native_workspace_bundle.sh --full output missing: {token}"


def test_native_workspace_scope_script_can_print_full_git_add_command() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "list_native_workspace_bundle.sh"
    assert script.is_file(), f"Missing {script}"

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script), "--full", "--git-add-cmd"],
        text=True,
        capture_output=True,
        cwd=repo_root,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""
    for token in (
        "git add --",
        "README.md",
        "docs/VERIFICATION.md",
        "src/yuantus/api/routers/plm_workspace.py",
        "src/yuantus/web/plm_workspace.html",
        "playwright/tests/plm_workspace_documents_ui.spec.js",
        "playwright/tests/plm_workspace_eco_actions.spec.js",
        "scripts/list_native_workspace_bundle.sh",
        "scripts/verify_playwright_plm_workspace_all.sh",
        "scripts/verify_playwright_plm_workspace_eco_actions.sh",
    ):
        assert token in out, f"list_native_workspace_bundle.sh --git-add-cmd output missing: {token}"


def test_native_workspace_scope_script_can_print_commit_plan() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "list_native_workspace_bundle.sh"
    assert script.is_file(), f"Missing {script}"

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script), "--full", "--commit-plan"],
        text=True,
        capture_output=True,
        cwd=repo_root,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""
    for token in (
        "Suggested commit title:",
        "feat(plm-workspace): land native workspace browser harness bundle",
        "Suggested commit body:",
        "Suggested staging command:",
        "git add --",
        "src/yuantus/api/app.py",
        "src/yuantus/api/routers/workbench.py",
        "src/yuantus/web/plm_workspace.html",
        "README.md",
        "scripts/verify_all.sh",
        "scripts/verify_playwright_plm_workspace_eco_actions.sh",
    ):
        assert token in out, f"list_native_workspace_bundle.sh --commit-plan output missing: {token}"
