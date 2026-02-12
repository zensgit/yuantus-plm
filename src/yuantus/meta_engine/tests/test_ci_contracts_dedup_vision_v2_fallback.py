from __future__ import annotations

import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + src/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_dedup_vision_search_prefers_v2_and_falls_back_to_v1_with_mode_mapping() -> None:
    repo_root = _find_repo_root(Path(__file__))
    client_py = repo_root / "src" / "yuantus" / "integrations" / "dedup_vision.py"
    text = _read(client_py)

    assert "/api/v2/search" in text, "Dedup Vision client must prefer /api/v2/search when available."
    assert "/api/search" in text, "Dedup Vision client must fall back to legacy /api/search when needed."

    # Backward-compat mapping: v1 caller uses "accurate" while v2 expects "precise".
    assert re.search(r'v2_mode\s*=\s*"precise"\s*if\s*str\(mode\)', text), (
        "Dedup Vision client must map mode accurate->precise for v2 search."
    )

    # Ensure we fall back on v2 400 as well (invalid mode / schema mismatch etc.).
    assert re.search(r"status\s*not\s*in\s*\{[^}]*400[^}]*\}", text), (
        "Dedup Vision client v2 fallback set must include HTTP 400."
    )
