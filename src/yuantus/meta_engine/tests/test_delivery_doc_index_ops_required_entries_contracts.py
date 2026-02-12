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


def test_ops_section_keeps_required_runbook_anchors() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file()

    ops = _extract_h2_section(_read(index_path), "## Ops & Deployment")
    refs = re.findall(r"`([^`]+)`", ops)
    assert refs, "No backticked paths found in docs/DELIVERY_DOC_INDEX.md ## Ops & Deployment"

    required = {
        "docs/OPS_RUNBOOK_MT.md",
        "docs/ERROR_CODES_JOBS.md",
        "docs/RUNBOOK_RUNTIME.md",
        "docs/RUNBOOK_BACKUP_RESTORE.md",
        "docs/RUNBOOK_CI_CHANGE_SCOPE.md",
        "docs/RUNBOOK_STRICT_GATE.md",
    }
    missing = sorted(required - set(refs))
    assert not missing, (
        "Missing required ops anchors in docs/DELIVERY_DOC_INDEX.md ## Ops & Deployment:\n"
        + "\n".join(f"- {m}" for m in missing)
    )

