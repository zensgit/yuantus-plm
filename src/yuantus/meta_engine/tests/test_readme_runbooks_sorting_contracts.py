from __future__ import annotations

import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "README.md").is_file():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + README.md)")


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


def test_readme_runbooks_section_is_sorted_and_unique_by_primary_path() -> None:
    repo_root = _find_repo_root(Path(__file__))
    readme = repo_root / "README.md"
    assert readme.is_file()

    section = _extract_h2_section(_read(readme), "## Runbooks")

    paths: list[str] = []
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        refs = re.findall(r"`([^`]+)`", s)
        if refs:
            paths.append(refs[0])

    assert paths, "No backticked runbook paths found in README.md ## Runbooks"

    duplicates = sorted({p for p in paths if paths.count(p) > 1})
    assert not duplicates, (
        "Duplicate runbook paths found in README.md ## Runbooks:\n"
        + "\n".join(f"- {p}" for p in duplicates)
    )

    expected = sorted(paths)
    assert paths == expected, (
        "README.md ## Runbooks paths must stay sorted for stable maintenance.\n"
        "Current:\n"
        + "\n".join(f"- {p}" for p in paths)
        + "\nExpected:\n"
        + "\n".join(f"- {p}" for p in expected)
    )

