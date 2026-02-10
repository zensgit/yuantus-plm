from __future__ import annotations

import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def _looks_like_a_repo_path(text: str) -> bool:
    # Keep this intentionally simple and conservative: only validate segments that
    # are clearly meant to be file paths, and ignore inline command snippets.
    if not text or text.strip() != text:
        return False
    if " " in text or "\t" in text or "\n" in text:
        return False

    if text == "CHANGELOG.md":
        return True

    if text.startswith(("docs/", "scripts/", "configs/", ".github/")):
        return True

    # Backticked filenames are almost always repo-relative paths in this doc.
    return text.endswith((".md", ".txt", ".json", ".yml", ".yaml", ".sh", ".py"))


def test_delivery_doc_index_backticked_paths_exist() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()

    text = index_path.read_text(encoding="utf-8", errors="replace")
    segments = re.findall(r"`([^`]+)`", text)
    assert segments, "Expected at least one backticked path segment"

    missing: list[str] = []
    for seg in segments:
        if not _looks_like_a_repo_path(seg):
            continue
        if not (repo_root / seg).exists():
            missing.append(seg)

    assert not missing, "Missing referenced paths:\n" + "\n".join(f"- {m}" for m in missing)

