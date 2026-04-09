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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_native_workspace_playwright_aggregate_wrapper_calls_all_three_smokes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    wrapper = repo_root / "scripts" / "verify_playwright_plm_workspace_all.sh"
    assert wrapper.is_file(), f"Missing {wrapper}"

    text = _read(wrapper)
    for token in (
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        'BASE_URL="${1:-http://127.0.0.1:7910}"',
        '"$SCRIPT_DIR/verify_playwright_plm_workspace_documents_ui.sh" "$BASE_URL"',
        '"$SCRIPT_DIR/verify_playwright_plm_workspace_demo_resume.sh" "$BASE_URL"',
        '"$SCRIPT_DIR/verify_playwright_plm_workspace_document_handoff.sh" "$BASE_URL"',
    ):
        assert token in text, f"verify_playwright_plm_workspace_all.sh missing token: {token}"
