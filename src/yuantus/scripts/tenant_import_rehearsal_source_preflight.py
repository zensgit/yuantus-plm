from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from yuantus.scripts.tenant_import_rehearsal_plan import (
    SCHEMA_VERSION as PLAN_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_migration_dry_run import BASELINE_REVISION
from yuantus.scripts.tenant_schema import GLOBAL_TABLE_NAMES, build_tenant_metadata


SCHEMA_VERSION = "p3.4.2-source-preflight-v1"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _list_blockers(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _redact_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return ""


def _expected_columns_by_table(import_order: list[str]) -> dict[str, set[str]]:
    metadata = build_tenant_metadata()
    expected: dict[str, set[str]] = {}
    for table_name in import_order:
        table = metadata.tables.get(table_name)
        expected[table_name] = set(table.columns.keys()) if table is not None else set()
    return expected


def _empty_report(
    *,
    plan_json: Path,
    plan: dict[str, Any],
    source_url: str,
    blockers: list[str],
) -> dict[str, Any]:
    import_order = _as_str_list(plan.get("tenant_tables_in_import_order"))
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_json": str(plan_json),
        "plan_schema_version": plan.get("schema_version"),
        "tenant_id": _as_str(plan.get("tenant_id")),
        "target_schema": _as_str(plan.get("target_schema")),
        "source_url": _redact_url(source_url),
        "baseline_revision": _as_str(plan.get("baseline_revision")),
        "tenant_tables_expected": import_order,
        "source_tables_present": [],
        "missing_source_tables": [],
        "column_mismatches": {},
        "ready_for_importer_source": False,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def _validate_before_connect(
    *,
    plan: dict[str, Any],
    source_url: str,
    confirm_source_preflight: bool,
) -> list[str]:
    blockers: list[str] = []
    if not confirm_source_preflight:
        blockers.append("missing --confirm-source-preflight")
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        blockers.append(f"plan schema_version must be {PLAN_SCHEMA_VERSION}")
    if plan.get("ready_for_importer") is not True:
        blockers.append("plan report must have ready_for_importer=true")
    if _list_blockers(plan.get("blockers")):
        blockers.append("plan report must have no blockers")
    if plan.get("baseline_revision") != BASELINE_REVISION:
        blockers.append(f"plan baseline_revision must be {BASELINE_REVISION}")
    if not source_url:
        blockers.append("missing source_url")

    import_order = _as_str_list(plan.get("tenant_tables_in_import_order"))
    if not import_order:
        blockers.append("plan tenant_tables_in_import_order must be non-empty")
    global_tables_in_plan = sorted(set(import_order) & set(GLOBAL_TABLE_NAMES))
    if global_tables_in_plan:
        blockers.append(
            "plan includes global/control-plane tables: "
            + ", ".join(global_tables_in_plan)
        )
    return blockers


def _inspect_columns(connection, table_name: str) -> set[str]:
    return {str(column["name"]) for column in inspect(connection).get_columns(table_name)}


def build_source_preflight_report(
    *,
    plan_json: str | Path,
    source_url: str,
    confirm_source_preflight: bool,
) -> dict[str, Any]:
    """Read-only source schema validation before import rehearsal execution."""
    plan_path = Path(plan_json)
    plan = _read_json(plan_path)
    source_url = _as_str(source_url).strip()
    blockers = _validate_before_connect(
        plan=plan,
        source_url=source_url,
        confirm_source_preflight=confirm_source_preflight,
    )
    report = _empty_report(
        plan_json=plan_path,
        plan=plan,
        source_url=source_url,
        blockers=blockers,
    )
    if blockers:
        return report

    import_order = _as_str_list(plan.get("tenant_tables_in_import_order"))
    expected_columns = _expected_columns_by_table(import_order)
    missing_metadata_tables = sorted(
        table_name for table_name, columns in expected_columns.items() if not columns
    )
    if missing_metadata_tables:
        report["blockers"].append(
            "plan includes tables missing from tenant metadata: "
            + ", ".join(missing_metadata_tables[:10])
            + ("..." if len(missing_metadata_tables) > 10 else "")
        )
        return report

    engine = create_engine(source_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            source_tables = set(inspector.get_table_names())
            source_columns = {
                table_name: _inspect_columns(connection, table_name)
                for table_name in import_order
                if table_name in source_tables
            }
    finally:
        engine.dispose()

    missing_source_tables = sorted(set(import_order) - source_tables)
    column_mismatches: dict[str, dict[str, list[str]]] = {}
    for table_name in import_order:
        if table_name not in source_columns:
            continue
        missing_columns = sorted(expected_columns[table_name] - source_columns[table_name])
        extra_columns = sorted(source_columns[table_name] - expected_columns[table_name])
        if missing_columns or extra_columns:
            column_mismatches[table_name] = {
                "missing_columns": missing_columns,
                "extra_columns": extra_columns,
            }

    if missing_source_tables:
        blockers.append(
            "source missing planned tenant tables: "
            + ", ".join(missing_source_tables[:10])
            + ("..." if len(missing_source_tables) > 10 else "")
        )
    missing_column_tables = [
        table_name
        for table_name, mismatch in column_mismatches.items()
        if mismatch["missing_columns"]
    ]
    if missing_column_tables:
        blockers.append(
            "source missing required columns for planned tables: "
            + ", ".join(missing_column_tables[:10])
            + ("..." if len(missing_column_tables) > 10 else "")
        )

    report.update(
        {
            "source_tables_present": sorted(source_tables & set(import_order)),
            "missing_source_tables": missing_source_tables,
            "column_mismatches": column_mismatches,
            "ready_for_importer_source": not blockers,
            "blockers": blockers,
        }
    )
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Source Preflight Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for importer source: `{str(report['ready_for_importer_source']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Source URL: `{report['source_url']}`",
        f"- Baseline revision: `{report['baseline_revision']}`",
        f"- Plan JSON: `{report['plan_json']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(["", "## Tenant Tables Expected", ""])
    lines.extend(f"- `{table}`" for table in report["tenant_tables_expected"])
    if not report["tenant_tables_expected"]:
        lines.append("- None")
    lines.extend(["", "## Source Tables Present", ""])
    lines.extend(f"- `{table}`" for table in report["source_tables_present"])
    if not report["source_tables_present"]:
        lines.append("- None")
    lines.extend(["", "## Missing Source Tables", ""])
    lines.extend(f"- `{table}`" for table in report["missing_source_tables"])
    if not report["missing_source_tables"]:
        lines.append("- None")
    lines.extend(["", "## Column Mismatches", ""])
    if report["column_mismatches"]:
        for table_name, mismatch in report["column_mismatches"].items():
            lines.append(f"- `{table_name}`")
            lines.append(
                f"  - missing: {', '.join(mismatch['missing_columns']) or 'none'}"
            )
            lines.append(f"  - extra: {', '.join(mismatch['extra_columns']) or 'none'}")
    else:
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_source_preflight",
        description="Read-only P3.4.2 source schema preflight before import rehearsal.",
    )
    parser.add_argument("--plan-json", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--confirm-source-preflight",
        action="store_true",
        help="Required before opening a source DB connection.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when the generated preflight report contains blockers.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_source_preflight_report(
            plan_json=args.plan_json,
            source_url=args.source_url,
            confirm_source_preflight=args.confirm_source_preflight,
        )
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
