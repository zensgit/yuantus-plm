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
        # Next H2 starts another section.
        if lines[j].startswith("## "):
            end = j
            break

    return "\n".join(lines[start:end]).strip()


def _extract_backticked_segments(text: str) -> set[str]:
    segs = re.findall(r"`([^`]+)`", text)
    return {s.strip() for s in segs if s.strip()}


def test_all_dev_and_verification_docs_are_indexed_in_delivery_doc_index_section() -> None:
    repo_root = _find_repo_root(Path(__file__))

    docs = sorted((repo_root / "docs").glob("DEV_AND_VERIFICATION_*.md"))
    assert docs, "No docs/DEV_AND_VERIFICATION_*.md files found; expected at least one"
    doc_paths = [p.relative_to(repo_root).as_posix() for p in docs]

    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()
    section = _extract_h2_section(_read(index_path), "## Development & Verification")
    assert section, "docs/DELIVERY_DOC_INDEX.md '## Development & Verification' section is empty"

    section_refs = _extract_backticked_segments(section)
    missing = [p for p in doc_paths if p not in section_refs]
    assert not missing, (
        "DEV_AND_VERIFICATION docs missing from docs/DELIVERY_DOC_INDEX.md under ## Development & Verification:\n"
        + "\n".join(f"- {p}" for p in missing)
    )

