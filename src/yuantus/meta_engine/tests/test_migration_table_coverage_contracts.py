from __future__ import annotations

import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "migrations").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + migrations/)")


def _migration_create_tables(repo_root: Path) -> set[str]:
    versions_dir = repo_root / "migrations" / "versions"
    assert versions_dir.is_dir(), f"Missing migrations versions dir: {versions_dir}"

    pattern = re.compile(r"""op\.create_table\(\s*["']([^"']+)["']""")
    names: set[str] = set()
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        names.update(pattern.findall(text))
    return names


def _declared_table_names(repo_root: Path) -> set[str]:
    src_dir = repo_root / "src" / "yuantus"
    assert src_dir.is_dir(), f"Missing source dir: {src_dir}"

    tablename_pattern = re.compile(r"""__tablename__\s*=\s*["']([^"']+)["']""")
    table_pattern = re.compile(r"""\bTable\(\s*["']([^"']+)["']""")

    names: set[str] = set()
    for path in sorted(src_dir.rglob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        # Keep contracts lightweight: avoid scanning tests, which can contain unrelated strings.
        if rel.startswith("src/yuantus/meta_engine/tests/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        names.update(tablename_pattern.findall(text))
        names.update(table_pattern.findall(text))
    return names


def test_every_declared_table_has_a_create_table_migration() -> None:
    repo_root = _find_repo_root(Path(__file__))
    migrated_tables = _migration_create_tables(repo_root)
    declared_tables = _declared_table_names(repo_root)

    missing = sorted(declared_tables - migrated_tables)
    assert not missing, (
        "Some declared ORM/association tables have no op.create_table migration contract. "
        "Add migration coverage for:\n"
        + "\n".join(f"- {name}" for name in missing)
    )


def test_migration_only_tables_are_allowlisted() -> None:
    repo_root = _find_repo_root(Path(__file__))
    migrated_tables = _migration_create_tables(repo_root)
    declared_tables = _declared_table_names(repo_root)

    extra = sorted(migrated_tables - declared_tables)
    assert not extra, (
        "Migrations define tables not declared under src/yuantus. "
        "If intentional, extend the scanner or document why the ORM is missing these:\n"
        + "\n".join(f"- {name}" for name in extra)
    )

