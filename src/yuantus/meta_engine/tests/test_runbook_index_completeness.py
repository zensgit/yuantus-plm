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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_runbooks_section(text: str) -> str:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Runbooks":
            start = i + 1
            break
    assert start is not None, "README.md missing '## Runbooks' section"

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


def test_all_runbooks_are_indexed_in_readme_and_delivery_doc_index() -> None:
    repo_root = _find_repo_root(Path(__file__))

    runbooks = sorted((repo_root / "docs").glob("RUNBOOK_*.md"))
    assert runbooks, "No docs/RUNBOOK_*.md files found; expected at least one runbook"

    runbook_paths = [p.relative_to(repo_root).as_posix() for p in runbooks]

    readme = repo_root / "README.md"
    assert readme.is_file()
    section = _extract_runbooks_section(_read(readme))
    assert section, "README.md Runbooks section is empty"

    readme_refs = _extract_backticked_segments(section)
    missing_from_readme = [p for p in runbook_paths if p not in readme_refs]
    assert not missing_from_readme, (
        "Runbooks missing from README.md ## Runbooks section:\n"
        + "\n".join(f"- {p}" for p in missing_from_readme)
    )

    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()
    index_refs = _extract_backticked_segments(_read(index_path))
    missing_from_index = [p for p in runbook_paths if p not in index_refs]
    assert not missing_from_index, (
        "Runbooks missing from docs/DELIVERY_DOC_INDEX.md:\n"
        + "\n".join(f"- {p}" for p in missing_from_index)
    )

