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


def _extract_contract_checks_block(ci_workflow_text: str) -> str:
    lines = ci_workflow_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "- name: Contract checks (perf workflows + delivery doc index)":
            start = i
            break
    assert start is not None, "Missing CI contracts step: 'Contract checks (perf workflows + delivery doc index)'"

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^  [a-zA-Z0-9_-]+:\s*$", lines[j]):
            end = j
            break

    return "\n".join(lines[start:end])


def test_ci_contracts_test_list_is_sorted_and_unique() -> None:
    repo_root = _find_repo_root(Path(__file__))
    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    assert ci_yml.is_file()

    block = _extract_contract_checks_block(_read(ci_yml))
    paths = re.findall(r"src/yuantus/meta_engine/tests/test_[a-zA-Z0-9_]+\.py", block)
    assert paths, "No test paths found in CI contracts step"

    duplicates = sorted({p for p in paths if paths.count(p) > 1})
    assert not duplicates, (
        "CI contracts step contains duplicate test entries:\n"
        + "\n".join(f"- {p}" for p in duplicates)
    )

    expected = sorted(paths)
    assert paths == expected, (
        "CI contracts step test list must stay path-sorted for stable maintenance.\n"
        "Current:\n"
        + "\n".join(f"- {p}" for p in paths)
        + "\nExpected:\n"
        + "\n".join(f"- {p}" for p in expected)
    )

