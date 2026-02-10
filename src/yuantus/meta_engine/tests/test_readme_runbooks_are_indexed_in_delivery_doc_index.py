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
        if lines[j].startswith("## "):
            end = j
            break

    return "\n".join(lines[start:end]).strip()


def test_readme_runbooks_are_indexed_in_delivery_doc_index() -> None:
    repo_root = _find_repo_root(Path(__file__))

    readme = repo_root / "README.md"
    assert readme.is_file()
    section = _extract_runbooks_section(_read(readme))
    assert section, "README.md Runbooks section is empty"

    referenced: list[str] = []
    for line in section.splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        for p in re.findall(r"`([^`]+)`", s):
            p = p.strip()
            if not p or "://" in p:
                continue
            referenced.append(p)

    assert referenced, "No backticked runbook paths found in README.md ## Runbooks"

    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()
    index_segments = {s.strip() for s in re.findall(r"`([^`]+)`", _read(index_path)) if s.strip()}

    missing = [p for p in referenced if p not in index_segments]
    assert not missing, (
        "README.md Runbooks paths missing from docs/DELIVERY_DOC_INDEX.md:\n"
        + "\n".join(f"- {p}" for p in missing)
    )

