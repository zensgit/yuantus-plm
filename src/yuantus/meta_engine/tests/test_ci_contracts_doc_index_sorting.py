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


def test_ci_contract_entries_are_sorted_in_delivery_doc_index() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()

    section = _extract_h2_section(_read(index_path), "## Development & Verification")
    refs_in_order = re.findall(r"`(docs/DEV_AND_VERIFICATION_CI_CONTRACTS_[^` ]+\.md)`", section)
    assert refs_in_order, "No CI contracts entries found in Delivery Doc Index development section"

    expected = sorted(refs_in_order)
    assert refs_in_order == expected, (
        "CI contracts entries under docs/DELIVERY_DOC_INDEX.md > ## Development & Verification "
        "must be sorted by path for stable maintenance.\n"
        "Current:\n"
        + "\n".join(f"- {p}" for p in refs_in_order)
        + "\nExpected:\n"
        + "\n".join(f"- {p}" for p in expected)
    )

