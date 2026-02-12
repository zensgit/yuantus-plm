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


def test_core_section_keeps_required_delivery_anchors() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()

    core = _extract_h2_section(_read(index_path), "## Core")
    refs = re.findall(r"`([^`]+)`", core)
    assert refs, "No backticked paths found in docs/DELIVERY_DOC_INDEX.md ## Core"

    # Hard anchors expected to remain stable.
    for required in ("CHANGELOG.md", "docs/VERIFICATION_RESULTS.md"):
        assert required in refs, f"Missing required core anchor: {required}"

    # Category anchors expected in core; allow dated filenames to roll forward.
    patterns = {
        "release_notes": r"^docs/RELEASE_NOTES_.*\.md$",
        "delivery_checklist": r"^docs/DELIVERY_CHECKLIST_.*\.md$",
        "delivery_summary": r"^docs/DELIVERY_SUMMARY_.*\.md$",
        "package_manifest": r"^docs/DELIVERY_PACKAGE_MANIFEST_.*\.txt$",
    }

    for label, pat in patterns.items():
        assert any(re.match(pat, r) for r in refs), (
            f"Missing required core category anchor ({label}); expected path matching: {pat}"
        )

