from __future__ import annotations

import re
from pathlib import Path


SECTIONS = (
    "## Core",
    "## Ops & Deployment",
    "## Product/UI Integration",
    "## Verification Reports (Latest)",
    "## Development & Verification",
    "## Optional",
    "## External (Not Included in Package)",
)


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


def _primary_paths(section_text: str) -> list[str]:
    paths: list[str] = []
    for line in section_text.splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        refs = re.findall(r"`([^`]+)`", s)
        if refs:
            paths.append(refs[0])
    return paths


def test_delivery_doc_index_major_sections_are_sorted_and_unique_by_primary_path() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()
    text = _read(index_path)

    for section_name in SECTIONS:
        section = _extract_h2_section(text, section_name)
        paths = _primary_paths(section)
        assert paths, f"No backticked path entries found in {section_name}"

        duplicates = sorted({p for p in paths if paths.count(p) > 1})
        assert not duplicates, (
            f"Duplicate primary paths found in {section_name}:\n"
            + "\n".join(f"- {p}" for p in duplicates)
        )

        expected = sorted(paths)
        assert paths == expected, (
            f"Primary paths under {section_name} must stay sorted for stable maintenance.\n"
            "Current:\n"
            + "\n".join(f"- {p}" for p in paths)
            + "\nExpected:\n"
            + "\n".join(f"- {p}" for p in expected)
        )

