from __future__ import annotations

import re
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


def _extract_h2_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i + 1
            break
    assert start is not None, f"Missing section: {heading!r}"

    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def test_development_and_verification_section_paths_are_sorted_and_unique() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()

    section = _extract_h2_section(_read(index_path), "## Development & Verification")
    paths = re.findall(r"`([^`]+)`", section)
    assert paths, "No backticked path entries found in Development & Verification section"

    duplicates = sorted({p for p in paths if paths.count(p) > 1})
    assert not duplicates, (
        "Duplicate paths found in docs/DELIVERY_DOC_INDEX.md > ## Development & Verification:\n"
        + "\n".join(f"- {p}" for p in duplicates)
    )

    expected = sorted(paths)
    assert paths == expected, (
        "Paths under docs/DELIVERY_DOC_INDEX.md > ## Development & Verification "
        "must stay sorted for stable maintenance.\n"
        "Current:\n"
        + "\n".join(f"- {p}" for p in paths)
        + "\nExpected:\n"
        + "\n".join(f"- {p}" for p in expected)
    )

