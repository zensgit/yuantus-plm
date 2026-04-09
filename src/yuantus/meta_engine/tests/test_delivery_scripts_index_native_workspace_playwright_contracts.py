from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "docs").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + docs/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_delivery_scripts_index_mentions_native_workspace_playwright_wrappers() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    assert index_path.is_file(), f"Missing {index_path}"

    text = _read(index_path)
    for token in (
        "verify_playwright_plm_workspace_all.sh",
        "verify_playwright_plm_workspace_documents_ui.sh",
        "verify_playwright_plm_workspace_demo_resume.sh",
        "verify_playwright_plm_workspace_document_handoff.sh",
        "Native workspace Playwright wrappers require Playwright installed in `node_modules`",
    ):
        assert token in text, f"docs/DELIVERY_SCRIPTS_INDEX_20260202.md missing token: {token}"
