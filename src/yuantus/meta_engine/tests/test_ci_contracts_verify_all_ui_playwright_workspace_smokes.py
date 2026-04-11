from __future__ import annotations

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


def test_verify_all_wires_native_workspace_playwright_smokes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    text = verify_all.read_text(encoding="utf-8")

    for token in (
        'run_test "UI Playwright Workspace Documents"',
        '"$SCRIPT_DIR/verify_playwright_plm_workspace_documents_ui.sh"',
        'run_test "UI Playwright Workspace Demo Resume"',
        '"$SCRIPT_DIR/verify_playwright_plm_workspace_demo_resume.sh"',
        'run_test "UI Playwright Workspace Document Handoff"',
        '"$SCRIPT_DIR/verify_playwright_plm_workspace_document_handoff.sh"',
        'run_test "UI Playwright Workspace ECO Actions"',
        '"$SCRIPT_DIR/verify_playwright_plm_workspace_eco_actions.sh"',
        'skip_test "UI Playwright Workspace Documents" "playwright not installed"',
        'skip_test "UI Playwright Workspace Demo Resume" "playwright not installed"',
        'skip_test "UI Playwright Workspace Document Handoff" "playwright not installed"',
        'skip_test "UI Playwright Workspace ECO Actions" "playwright not installed"',
        'skip_test "UI Playwright Workspace Documents" "RUN_UI_PLAYWRIGHT=0"',
        'skip_test "UI Playwright Workspace Demo Resume" "RUN_UI_PLAYWRIGHT=0"',
        'skip_test "UI Playwright Workspace Document Handoff" "RUN_UI_PLAYWRIGHT=0"',
        'skip_test "UI Playwright Workspace ECO Actions" "RUN_UI_PLAYWRIGHT=0"',
        'skip_test "UI Playwright Workspace Documents" "RUN_UI_AGG=0"',
        'skip_test "UI Playwright Workspace Demo Resume" "RUN_UI_AGG=0"',
        'skip_test "UI Playwright Workspace Document Handoff" "RUN_UI_AGG=0"',
        'skip_test "UI Playwright Workspace ECO Actions" "RUN_UI_AGG=0"',
    ):
        assert token in text, f"verify_all.sh missing native workspace UI Playwright token: {token}"
