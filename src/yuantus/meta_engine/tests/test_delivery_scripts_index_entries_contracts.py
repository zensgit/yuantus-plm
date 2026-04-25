from __future__ import annotations

import subprocess
from pathlib import Path


PACKAGE_ONLY_ENTRIES = {
    "backup.sh",
    "restore.sh",
    "verify_extract_start.sh",
    "verify_package.sh",
}


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def _indexed_scripts(index_text: str) -> list[str]:
    entries: list[str] = []
    for line in index_text.splitlines():
        if line.strip() == "## Notes":
            break
        if line.startswith("- "):
            entries.append(line.removeprefix("- ").strip())
    return entries


def test_delivery_scripts_index_entries_are_unique_and_exist() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    entries = _indexed_scripts(index_path.read_text(encoding="utf-8", errors="replace"))
    delivery_tree = (repo_root / "docs" / "DELIVERY_TREE_20260202.md").read_text(
        encoding="utf-8",
        errors="replace",
    )

    assert entries, "DELIVERY_SCRIPTS_INDEX must list script entries before notes"

    duplicates = sorted({entry for entry in entries if entries.count(entry) > 1})
    assert duplicates == []

    missing = sorted(
        entry
        for entry in entries
        if entry not in PACKAGE_ONLY_ENTRIES and not (repo_root / "scripts" / entry).is_file()
    )
    assert missing == []

    missing_package_only_docs = sorted(
        entry for entry in PACKAGE_ONLY_ENTRIES if f"├── {entry}" not in delivery_tree
    )
    assert missing_package_only_docs == []


def test_delivery_scripts_index_repo_local_shell_entries_are_syntax_valid() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    entries = _indexed_scripts(index_path.read_text(encoding="utf-8", errors="replace"))

    failures: list[str] = []
    for entry in entries:
        if not entry.endswith(".sh") or entry in PACKAGE_ONLY_ENTRIES:
            continue

        script = repo_root / "scripts" / entry
        if not script.is_file():
            continue

        cp = subprocess.run(  # noqa: S603,S607
            ["bash", "-n", str(script)],
            text=True,
            capture_output=True,
        )
        if cp.returncode != 0:
            failures.append(f"{entry}\n{cp.stdout}\n{cp.stderr}".strip())

    assert failures == []
