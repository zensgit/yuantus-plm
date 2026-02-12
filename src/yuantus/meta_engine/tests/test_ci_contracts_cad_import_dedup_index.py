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


def test_cad_import_supports_dedup_index_flag_and_enqueues_payload() -> None:
    repo_root = _find_repo_root(Path(__file__))
    cad_router = repo_root / "src" / "yuantus" / "meta_engine" / "web" / "cad_router.py"
    assert cad_router.is_file()

    text = _read(cad_router)

    assert re.search(r"\bdedup_index\s*:\s*bool\s*=\s*Form\(", text), (
        "cad/import should expose dedup_index: bool = Form(...) for triggering Dedup Vision indexing."
    )

    assert '"index": bool(dedup_index)' in text, (
        "cad/import should pass index flag into cad_dedup_vision job payload "
        "(expected exact snippet: '\"index\": bool(dedup_index)')."
    )

