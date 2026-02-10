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


def test_readme_runbooks_reference_existing_files() -> None:
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
        # Runbooks list uses backticks around file paths.
        paths = re.findall(r"`([^`]+)`", s)
        for p in paths:
            p = p.strip()
            if not p:
                continue
            referenced.append(p)

    assert referenced, "No backticked file paths found under README.md Runbooks section"

    missing: list[str] = []
    for rel in referenced:
        # Only validate repo-relative paths (not URLs or code samples).
        if "://" in rel:
            continue
        if rel.startswith("/"):
            # README should not reference absolute paths.
            missing.append(rel)
            continue
        target = repo_root / rel
        if not target.exists():
            missing.append(rel)

    assert not missing, f"README.md Runbooks references missing paths: {missing}"

