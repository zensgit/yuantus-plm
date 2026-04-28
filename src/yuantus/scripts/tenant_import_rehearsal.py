from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, create_engine, insert, select
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts.tenant_migration_dry_run import _build_import_metadata
from yuantus.scripts.tenant_schema import GLOBAL_TABLE_NAMES


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-v1"
_PACKET_SCHEMA_VERSION = packet.SCHEMA_VERSION
_REQUIRED_PACKET_FIELDS = (
    "next_action_json",
    "tenant_id",
    "target_schema",
    "target_url",
    "dry_run_json",
    "readiness_json",
    "handoff_json",
    "plan_json",
    "source_preflight_json",
    "target_preflight_json",
)
_DEFAULT_BATCH_SIZE = 500
_TARGET_SCHEMA_RE = re.compile(r"^yt_t_[a-z0-9_]+$")


def _read_json_object(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.is_file():
        return None, f"{path} does not exist"
    try:
        value = json.loads(path.read_text())
    except Exception as exc:
        return None, f"{path} is not valid JSON: {exc}"
    if not isinstance(value, dict):
        return None, f"{path} must contain a JSON object"
    return value, ""


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_int_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        key: count
        for key, count in value.items()
        if isinstance(key, str) and isinstance(count, int)
    }


def _redact_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return ""


def _is_postgres_url(url: str) -> bool:
    try:
        drivername = make_url(url).drivername
    except Exception:
        return False
    return drivername.startswith("postgresql") or drivername.startswith("postgres")


def _validate_packet(
    implementation_packet_json: Path,
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    packet_report, read_error = _read_json_object(implementation_packet_json)
    blockers: list[str] = []
    if read_error:
        return {}, [f"implementation packet {read_error}"], {}
    assert packet_report is not None

    if packet_report.get("schema_version") != _PACKET_SCHEMA_VERSION:
        blockers.append(
            f"implementation packet schema_version must be {_PACKET_SCHEMA_VERSION}"
        )
    if packet_report.get("ready_for_claude_importer") is not True:
        blockers.append(
            "implementation packet must have ready_for_claude_importer=true"
        )
    if packet_report.get("ready_for_cutover") is not False:
        blockers.append("implementation packet must have ready_for_cutover=false")
    if _as_list(packet_report.get("blockers")):
        blockers.append("implementation packet must have no blockers")

    for key in _REQUIRED_PACKET_FIELDS:
        if not _as_str(packet_report.get(key)):
            blockers.append(f"implementation packet missing {key}")
    target_schema = _as_str(packet_report.get("target_schema"))
    if target_schema and not _TARGET_SCHEMA_RE.fullmatch(target_schema):
        blockers.append("target_schema must match ^yt_t_[a-z0-9_]+$")

    fresh_report: dict[str, Any] = {}
    next_action_json = _as_str(packet_report.get("next_action_json"))
    if next_action_json:
        try:
            fresh_report = packet.build_implementation_packet_report(
                next_action_json,
                output_md=_as_str(packet_report.get("implementation_md"))
                or "tenant_import_rehearsal_scaffold.md",
            )
        except Exception as exc:
            blockers.append(f"fresh implementation packet validation failed: {exc}")
        else:
            for blocker in _as_list(fresh_report.get("blockers")):
                blockers.append(f"fresh {blocker}")
            if fresh_report.get("ready_for_claude_importer") is not True:
                blockers.append(
                    "fresh implementation packet validation must have "
                    "ready_for_claude_importer=true"
                )
            for key in _REQUIRED_PACKET_FIELDS:
                if _as_str(packet_report.get(key)) != _as_str(fresh_report.get(key)):
                    blockers.append(
                        f"implementation packet {key} must match fresh validation"
                    )

    return packet_report, blockers, fresh_report


def _load_plan(packet_report: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    plan_path = Path(_as_str(packet_report.get("plan_json")))
    plan, read_error = _read_json_object(plan_path)
    if read_error:
        return {}, [f"plan artifact {read_error}"]
    assert plan is not None
    return plan, []


def _validate_execution_inputs(
    *,
    packet_report: dict[str, Any],
    plan: dict[str, Any],
    source_url: str,
    target_url: str,
    batch_size: int,
) -> list[str]:
    blockers: list[str] = []
    if not source_url:
        blockers.append("missing --source-url")
    if not target_url:
        blockers.append("missing --target-url")
    elif not _is_postgres_url(target_url):
        blockers.append("target_url must be a PostgreSQL URL")
    if batch_size <= 0:
        blockers.append("batch_size must be positive")
    target_schema = _as_str(packet_report.get("target_schema"))
    if not _TARGET_SCHEMA_RE.fullmatch(target_schema):
        blockers.append("target_schema must match ^yt_t_[a-z0-9_]+$")

    source_url_redacted = _redact_url(source_url) if source_url else ""
    target_url_redacted = _redact_url(target_url) if target_url else ""
    if _as_str(plan.get("source_url")) and source_url_redacted != plan.get("source_url"):
        blockers.append("source_url must match redacted plan source_url")
    if (
        _as_str(packet_report.get("target_url"))
        and target_url_redacted != packet_report.get("target_url")
    ):
        blockers.append("target_url must match redacted implementation packet target_url")

    import_order = _as_str_list(plan.get("tenant_tables_in_import_order"))
    if not import_order:
        blockers.append("plan tenant_tables_in_import_order must be non-empty")
    global_tables = sorted(set(import_order) & set(GLOBAL_TABLE_NAMES))
    if global_tables:
        blockers.append(
            "plan includes global/control-plane tables: " + ", ".join(global_tables)
        )

    source_row_counts = _as_int_map(plan.get("source_row_counts"))
    missing_row_counts = sorted(set(import_order) - set(source_row_counts))
    if missing_row_counts:
        blockers.append(
            "plan source_row_counts missing import tables: "
            + ", ".join(missing_row_counts[:10])
            + ("..." if len(missing_row_counts) > 10 else "")
        )

    metadata = _build_import_metadata()
    missing_metadata = sorted(
        table_name for table_name in import_order if table_name not in metadata.tables
    )
    if missing_metadata:
        blockers.append(
            "plan includes tables missing from tenant metadata: "
            + ", ".join(missing_metadata[:10])
            + ("..." if len(missing_metadata) > 10 else "")
        )
    return blockers


def _tenant_tables_for_import(
    import_order: list[str],
    target_schema: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_metadata = _build_import_metadata()
    target_metadata = MetaData()
    source_tables: dict[str, Any] = {}
    target_tables: dict[str, Any] = {}
    for table_name in import_order:
        source_table = source_metadata.tables[table_name]
        target_table = source_table.to_metadata(target_metadata, schema=target_schema)
        source_tables[table_name] = source_table
        target_tables[table_name] = target_table
    return source_tables, target_tables


def _copy_table(
    *,
    source_connection,
    target_connection,
    source_table,
    target_table,
    batch_size: int,
) -> int:
    inserted = 0
    result = source_connection.execute(select(source_table))
    while True:
        rows = [dict(row) for row in result.mappings().fetchmany(batch_size)]
        if not rows:
            break
        target_connection.execute(insert(target_table), rows)
        inserted += len(rows)
    return inserted


def _execute_row_copy(
    *,
    source_url: str,
    target_url: str,
    target_schema: str,
    import_order: list[str],
    source_row_counts: dict[str, int],
    batch_size: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    source_tables, target_tables = _tenant_tables_for_import(import_order, target_schema)
    table_results: list[dict[str, Any]] = []
    blockers: list[str] = []

    source_engine = create_engine(source_url, poolclass=NullPool)
    target_engine = create_engine(target_url, poolclass=NullPool)
    try:
        with source_engine.connect() as source_connection:
            with target_engine.begin() as target_connection:
                for table_name in import_order:
                    inserted = _copy_table(
                        source_connection=source_connection,
                        target_connection=target_connection,
                        source_table=source_tables[table_name],
                        target_table=target_tables[table_name],
                        batch_size=batch_size,
                    )
                    expected = source_row_counts.get(table_name)
                    matches = expected == inserted
                    table_results.append(
                        {
                            "table": table_name,
                            "source_rows_expected": expected,
                            "target_rows_inserted": inserted,
                            "row_count_matches": matches,
                        }
                    )
                    if not matches:
                        blockers.append(
                            f"{table_name} inserted {inserted} rows; expected {expected}"
                        )
    finally:
        source_engine.dispose()
        target_engine.dispose()

    return table_results, blockers


def build_rehearsal_scaffold_report(
    implementation_packet_json: str | Path,
    *,
    confirm_rehearsal: bool,
    source_url: str = "",
    target_url: str = "",
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Validate prerequisites and copy tenant rows for a rehearsal import."""
    packet_path = Path(implementation_packet_json)
    packet_report, packet_blockers, fresh_report = _validate_packet(packet_path)
    plan, plan_blockers = _load_plan(packet_report) if packet_report else ({}, [])
    blockers = list(packet_blockers)
    blockers.extend(plan_blockers)
    if not confirm_rehearsal:
        blockers.insert(0, "missing --confirm-rehearsal")
    if not blockers:
        blockers.extend(
            _validate_execution_inputs(
                packet_report=packet_report,
                plan=plan,
                source_url=source_url,
                target_url=target_url,
                batch_size=batch_size,
            )
        )
    guard_ready = not blockers
    table_results: list[dict[str, Any]] = []
    db_connection_attempted = False
    import_executed = False
    if guard_ready:
        db_connection_attempted = True
        import_order = _as_str_list(plan.get("tenant_tables_in_import_order"))
        source_row_counts = _as_int_map(plan.get("source_row_counts"))
        table_results, import_blockers = _execute_row_copy(
            source_url=source_url,
            target_url=target_url,
            target_schema=_as_str(packet_report.get("target_schema")),
            import_order=import_order,
            source_row_counts=source_row_counts,
            batch_size=batch_size,
        )
        blockers.extend(import_blockers)
        import_executed = not import_blockers

    return {
        "schema_version": SCHEMA_VERSION,
        "implementation_packet_json": str(packet_path),
        "implementation_packet_schema_version": packet_report.get("schema_version", ""),
        "ready_for_rehearsal_scaffold": guard_ready,
        "ready_for_import_execution": guard_ready,
        "ready_for_rehearsal_import": import_executed and not blockers,
        "import_executed": import_executed,
        "db_connection_attempted": db_connection_attempted,
        "ready_for_cutover": False,
        "tenant_id": _as_str(packet_report.get("tenant_id")),
        "target_schema": _as_str(packet_report.get("target_schema")),
        "source_url": _redact_url(source_url) if source_url else "",
        "target_url": (
            _redact_url(target_url)
            if target_url
            else _as_str(packet_report.get("target_url"))
        ),
        "batch_size": batch_size,
        "next_action_json": _as_str(packet_report.get("next_action_json")),
        "dry_run_json": _as_str(packet_report.get("dry_run_json")),
        "readiness_json": _as_str(packet_report.get("readiness_json")),
        "handoff_json": _as_str(packet_report.get("handoff_json")),
        "plan_json": _as_str(packet_report.get("plan_json")),
        "source_preflight_json": _as_str(packet_report.get("source_preflight_json")),
        "target_preflight_json": _as_str(packet_report.get("target_preflight_json")),
        "fresh_artifact_validations": fresh_report.get("artifact_validations", []),
        "tables_planned": _as_str_list(plan.get("tenant_tables_in_import_order")),
        "table_results": table_results,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    validations = report.get("fresh_artifact_validations") or []
    lines = [
        "# Tenant Import Rehearsal Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Scaffold guard passed: `{str(report['ready_for_rehearsal_scaffold']).lower()}`",
        f"- Rehearsal import passed: `{str(report['ready_for_rehearsal_import']).lower()}`",
        f"- Import executed: `{str(report['import_executed']).lower()}`",
        f"- DB connection attempted: `{str(report['db_connection_attempted']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Source URL: `{report['source_url']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Batch size: `{report['batch_size']}`",
        f"- Implementation packet JSON: `{report['implementation_packet_json']}`",
        f"- Next-action JSON: `{report['next_action_json']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Fresh Artifact Validation",
            "",
            "| Artifact | Schema version | Ready field | Ready | Path |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for validation in validations:
        lines.append(
            "| "
            f"`{validation['artifact']}` | "
            f"`{validation['schema_version']}` | "
            f"`{validation['ready_field']}` | "
            f"`{str(validation['ready']).lower()}` | "
            f"`{validation['path']}` |"
        )
    lines.extend(
        [
            "",
            "## Table Results",
            "",
            "| Table | Source rows expected | Target rows inserted | Matches |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for result in report.get("table_results") or []:
        lines.append(
            "| "
            f"`{result['table']}` | "
            f"{result['source_rows_expected']} | "
            f"{result['target_rows_inserted']} | "
            f"`{str(result['row_count_matches']).lower()}` |"
        )
    if not report.get("table_results"):
        lines.append("| None | 0 | 0 | `false` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This rehearsal imports tenant application rows only after the "
            "implementation packet and all upstream artifacts are revalidated. "
            "It never imports global/control-plane tables and never authorizes cutover.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal",
        description="Run a guarded P3.4.2 tenant import rehearsal row-copy.",
    )
    parser.add_argument("--implementation-packet-json", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument("--confirm-rehearsal", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the rehearsal import executes without blockers.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_rehearsal_scaffold_report(
            args.implementation_packet_json,
            confirm_rehearsal=args.confirm_rehearsal,
            source_url=args.source_url,
            target_url=args.target_url,
            batch_size=args.batch_size,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and (report["blockers"] or not report["import_executed"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
