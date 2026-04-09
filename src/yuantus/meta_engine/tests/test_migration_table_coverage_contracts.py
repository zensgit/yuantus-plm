from __future__ import annotations

import re
from pathlib import Path

_LEGACY_UNMIGRATED_TABLE_ALLOWLIST = (
    "meta_approval_categories",
    "meta_approval_requests",
    "meta_box_contents",
    "meta_box_items",
    "meta_cut_plans",
    "meta_cut_results",
    "meta_maintenance_categories",
    "meta_maintenance_equipment",
    "meta_maintenance_requests",
    "meta_quality_alerts",
    "meta_quality_checks",
    "meta_quality_points",
    "meta_raw_materials",
    "meta_report_locale_profiles",
    "meta_subcontract_order_events",
    "meta_subcontract_orders",
    "meta_sync_jobs",
    "meta_sync_records",
    "meta_sync_sites",
    "meta_translations",
)


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

    missing = sorted(
        (declared_tables - migrated_tables) - set(_LEGACY_UNMIGRATED_TABLE_ALLOWLIST)
    )
    assert not missing, (
        "Some declared ORM/association tables have no op.create_table migration contract. "
        "Add migration coverage for:\n"
        + "\n".join(f"- {name}" for name in missing)
    )


def test_legacy_unmigrated_table_allowlist_is_current_and_sorted() -> None:
    repo_root = _find_repo_root(Path(__file__))
    migrated_tables = _migration_create_tables(repo_root)
    declared_tables = _declared_table_names(repo_root)

    current_missing = declared_tables - migrated_tables
    allowlist_entries = list(_LEGACY_UNMIGRATED_TABLE_ALLOWLIST)
    allowlist = set(allowlist_entries)

    duplicates = sorted({name for name in allowlist_entries if allowlist_entries.count(name) > 1})
    assert not duplicates, (
        "Legacy unmigrated table allowlist must not contain duplicates:\n"
        + "\n".join(f"- {name}" for name in duplicates)
    )

    assert allowlist_entries == sorted(allowlist_entries), (
        "Legacy unmigrated table allowlist must stay sorted for stable maintenance."
    )

    stale = sorted(allowlist - current_missing)
    assert not stale, (
        "Legacy unmigrated table allowlist contains table(s) that are no longer missing migrations. "
        "Drop them from the allowlist:\n"
        + "\n".join(f"- {name}" for name in stale)
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
