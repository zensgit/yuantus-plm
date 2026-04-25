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


def test_odoo18_plm_stack_verifier_is_discoverable_from_scripts_index() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    text = index_path.read_text(encoding="utf-8", errors="replace")

    for token in (
        "verify_odoo18_plm_stack.sh",
        "Odoo18 PLM focused smoke suite",
        "`smoke` or `full` mode",
        'src/yuantus/meta_engine/web/*_router.py',
    ):
        assert token in text, f"DELIVERY_SCRIPTS_INDEX missing token: {token}"
