from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import ForeignKeyConstraint, create_engine, func, inspect, select
from sqlalchemy.engine import make_url

from yuantus.scripts.tenant_schema import (
    GLOBAL_TABLE_NAMES,
    build_tenant_metadata,
    resolve_schema_for_tenant_id,
)


SCHEMA_VERSION = "p3.4.1-dry-run-v1"
BASELINE_REVISION = "t1_initial_tenant_baseline"
ALLOWED_METADATA_TABLES = frozenset({"alembic_version"})


def _strip_cross_schema_fks(metadata):
    """Mirror the tenant baseline generator before sorting tenant tables."""
    for table in metadata.tables.values():
        to_remove: list[ForeignKeyConstraint] = []
        for cons in list(table.constraints):
            if not isinstance(cons, ForeignKeyConstraint):
                continue
            for elem in cons.elements:
                target_table = elem.target_fullname.split(".", 1)[0]
                if target_table in GLOBAL_TABLE_NAMES:
                    to_remove.append(cons)
                    break
        for cons in to_remove:
            for elem in list(cons.elements):
                if elem.parent is not None:
                    elem.parent.foreign_keys.discard(elem)
                table.foreign_keys.discard(elem)
            table.constraints.discard(cons)
    return metadata


def _build_import_metadata():
    return _strip_cross_schema_fks(build_tenant_metadata())


def _redact_source_url(source_url: str) -> str:
    return make_url(source_url).render_as_string(hide_password=True)


def _count_rows(connection, table) -> int:
    value = connection.execute(select(func.count()).select_from(table)).scalar_one()
    return int(value)


def build_dry_run_report(source_url: str, tenant_id: str) -> dict[str, Any]:
    """Inspect a source DB without moving data or touching a target DB."""
    source_url_redacted = _redact_source_url(source_url)
    target_schema = resolve_schema_for_tenant_id(tenant_id)
    metadata = _build_import_metadata()
    tenant_tables_in_import_order = [table.name for table in metadata.sorted_tables]
    tenant_table_names = set(tenant_tables_in_import_order)

    engine = create_engine(source_url)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            source_tables = sorted(inspector.get_table_names())
            source_table_names = set(source_tables)

            row_counts: dict[str, int] = {}
            for table_name in tenant_tables_in_import_order:
                if table_name in source_table_names:
                    row_counts[table_name] = _count_rows(
                        connection, metadata.tables[table_name]
                    )
    finally:
        engine.dispose()

    missing_tenant_tables = [
        table_name
        for table_name in tenant_tables_in_import_order
        if table_name not in source_table_names
    ]
    excluded_global_tables_present = sorted(source_table_names & set(GLOBAL_TABLE_NAMES))
    unknown_source_tables = sorted(
        source_table_names
        - tenant_table_names
        - set(GLOBAL_TABLE_NAMES)
        - set(ALLOWED_METADATA_TABLES)
    )

    blockers: list[str] = []
    if missing_tenant_tables:
        blockers.append(
            "Missing tenant tables: "
            f"{len(missing_tenant_tables)} "
            f"({', '.join(missing_tenant_tables[:10])}"
            f"{'...' if len(missing_tenant_tables) > 10 else ''})"
        )
    if unknown_source_tables:
        blockers.append(f"Unknown source tables: {', '.join(unknown_source_tables)}")

    return {
        "schema_version": SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "target_schema": target_schema,
        "source_url": source_url_redacted,
        "baseline_revision": BASELINE_REVISION,
        "global_tables": sorted(GLOBAL_TABLE_NAMES),
        "tenant_tables_in_import_order": tenant_tables_in_import_order,
        "source_tables": source_tables,
        "missing_tenant_tables": missing_tenant_tables,
        "excluded_global_tables_present": excluded_global_tables_present,
        "unknown_source_tables": unknown_source_tables,
        "row_counts": row_counts,
        "ready_for_import": not missing_tenant_tables and not unknown_source_tables,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Migration Dry-Run Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Source URL: `{report['source_url']}`",
        f"- Baseline revision: `{report['baseline_revision']}`",
        f"- Ready for import: `{str(report['ready_for_import']).lower()}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Source tables: {len(report['source_tables'])}",
            f"- Tenant tables in import order: {len(report['tenant_tables_in_import_order'])}",
            f"- Missing tenant tables: {len(report['missing_tenant_tables'])}",
            f"- Excluded global tables present: {len(report['excluded_global_tables_present'])}",
            f"- Unknown source tables: {len(report['unknown_source_tables'])}",
            "",
            "## Excluded Global Tables Present",
            "",
        ]
    )
    lines.extend(f"- `{name}`" for name in report["excluded_global_tables_present"])
    if not report["excluded_global_tables_present"]:
        lines.append("- None")
    lines.extend(["", "## Unknown Source Tables", ""])
    lines.extend(f"- `{name}`" for name in report["unknown_source_tables"])
    if not report["unknown_source_tables"]:
        lines.append("- None")
    lines.extend(["", "## Row Counts", ""])
    for table_name, count in report["row_counts"].items():
        lines.append(f"- `{table_name}`: {count}")
    if not report["row_counts"]:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m yuantus.scripts.tenant_migration_dry_run",
        description="Read-only P3.4.1 source DB inspection for tenant migration planning.",
    )
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when the generated report contains blockers.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_dry_run_report(args.source_url, args.tenant_id)
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and report["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
