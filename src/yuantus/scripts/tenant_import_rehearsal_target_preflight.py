from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from yuantus.scripts.tenant_import_rehearsal_plan import (
    SCHEMA_VERSION as PLAN_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_migration_dry_run import BASELINE_REVISION
from yuantus.scripts.tenant_schema import GLOBAL_TABLE_NAMES


SCHEMA_VERSION = "p3.4.2-target-preflight-v1"
_TARGET_SCHEMA_RE = re.compile(r"^yt_t_[a-z0-9_]+$")


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


def _is_postgres_url(url: str) -> bool:
    try:
        drivername = make_url(url).drivername
    except Exception:
        return False
    return drivername.startswith("postgresql") or drivername.startswith("postgres")


def _quote_schema(schema: str) -> str:
    if not _TARGET_SCHEMA_RE.fullmatch(schema):
        raise ValueError("target_schema must match ^yt_t_[a-z0-9_]+$")
    return f'"{schema}"'


def _empty_report(
    *,
    plan_json: Path,
    plan: dict[str, Any],
    target_url: str,
    target_schema: str,
    blockers: list[str],
) -> dict[str, Any]:
    import_order = _as_str_list(plan.get("tenant_tables_in_import_order"))
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_json": str(plan_json),
        "plan_schema_version": plan.get("schema_version"),
        "tenant_id": _as_str(plan.get("tenant_id")),
        "target_schema": target_schema,
        "target_url": _redact_url(target_url),
        "baseline_revision": _as_str(plan.get("baseline_revision")),
        "tenant_tables_expected": import_order,
        "tenant_tables_present": [],
        "missing_target_tables": [],
        "global_tables_present": [],
        "target_schema_exists": False,
        "alembic_version": "",
        "ready_for_importer_target": False,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def _validate_before_connect(
    *,
    plan: dict[str, Any],
    target_url: str,
    target_schema: str,
    confirm_target_preflight: bool,
) -> list[str]:
    blockers: list[str] = []
    if not confirm_target_preflight:
        blockers.append("missing --confirm-target-preflight")
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        blockers.append(f"plan schema_version must be {PLAN_SCHEMA_VERSION}")
    if plan.get("ready_for_importer") is not True:
        blockers.append("plan report must have ready_for_importer=true")
    if _list_blockers(plan.get("blockers")):
        blockers.append("plan report must have no blockers")
    if plan.get("baseline_revision") != BASELINE_REVISION:
        blockers.append(f"plan baseline_revision must be {BASELINE_REVISION}")
    if not target_url:
        blockers.append("missing target_url")
    elif not _is_postgres_url(target_url):
        blockers.append("target_url must be a PostgreSQL URL")
    if not target_schema:
        blockers.append("missing target_schema")
    elif not _TARGET_SCHEMA_RE.fullmatch(target_schema):
        blockers.append("target_schema must match ^yt_t_[a-z0-9_]+$")
    if target_schema and plan.get("target_schema") != target_schema:
        blockers.append("target_schema must match plan target_schema")

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


def _target_tables(connection, target_schema: str) -> set[str]:
    rows = connection.execute(
        text(
            "select table_name from information_schema.tables "
            "where table_schema = :schema and table_type = 'BASE TABLE'"
        ),
        {"schema": target_schema},
    )
    return {str(row[0]) for row in rows}


def _target_schema_exists(connection, target_schema: str) -> bool:
    return bool(
        connection.execute(
            text("select exists (select 1 from pg_namespace where nspname = :schema)"),
            {"schema": target_schema},
        ).scalar_one()
    )


def _target_alembic_version(connection, target_schema: str) -> str:
    quoted_schema = _quote_schema(target_schema)
    value = connection.execute(
        text(f"select version_num from {quoted_schema}.alembic_version")
    ).scalar_one_or_none()
    return str(value) if value is not None else ""


def build_target_preflight_report(
    *,
    plan_json: str | Path,
    target_url: str,
    target_schema: str,
    confirm_target_preflight: bool,
) -> dict[str, Any]:
    """Read-only target schema validation before import rehearsal execution."""
    plan_path = Path(plan_json)
    plan = _read_json(plan_path)
    target_url = _as_str(target_url).strip()
    target_schema = _as_str(target_schema).strip()

    blockers = _validate_before_connect(
        plan=plan,
        target_url=target_url,
        target_schema=target_schema,
        confirm_target_preflight=confirm_target_preflight,
    )
    report = _empty_report(
        plan_json=plan_path,
        plan=plan,
        target_url=target_url,
        target_schema=target_schema,
        blockers=blockers,
    )
    if blockers:
        return report

    import_order = _as_str_list(plan.get("tenant_tables_in_import_order"))
    engine = create_engine(target_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            schema_exists = _target_schema_exists(connection, target_schema)
            present_tables = _target_tables(connection, target_schema) if schema_exists else set()
            alembic_version = (
                _target_alembic_version(connection, target_schema)
                if "alembic_version" in present_tables
                else ""
            )
    finally:
        engine.dispose()

    missing_target_tables = sorted(set(import_order) - present_tables)
    global_tables_present = sorted(set(GLOBAL_TABLE_NAMES) & present_tables)
    if not schema_exists:
        blockers.append("target schema is missing")
    if alembic_version != BASELINE_REVISION:
        blockers.append(f"target alembic_version must be {BASELINE_REVISION}")
    if missing_target_tables:
        blockers.append(
            "target schema missing tenant tables: "
            + ", ".join(missing_target_tables[:10])
            + ("..." if len(missing_target_tables) > 10 else "")
        )
    if global_tables_present:
        blockers.append(
            "target schema contains global/control-plane tables: "
            + ", ".join(global_tables_present)
        )

    report.update(
        {
            "tenant_tables_present": sorted(present_tables - {"alembic_version"}),
            "missing_target_tables": missing_target_tables,
            "global_tables_present": global_tables_present,
            "target_schema_exists": schema_exists,
            "alembic_version": alembic_version,
            "ready_for_importer_target": not blockers,
            "blockers": blockers,
        }
    )
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Target Preflight Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for importer target: `{str(report['ready_for_importer_target']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Baseline revision: `{report['baseline_revision']}`",
        f"- Plan JSON: `{report['plan_json']}`",
        f"- Target schema exists: `{str(report['target_schema_exists']).lower()}`",
        f"- Alembic version: `{report['alembic_version']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(["", "## Tenant Tables Expected", ""])
    lines.extend(f"- `{table}`" for table in report["tenant_tables_expected"])
    if not report["tenant_tables_expected"]:
        lines.append("- None")
    lines.extend(["", "## Tenant Tables Present", ""])
    lines.extend(f"- `{table}`" for table in report["tenant_tables_present"])
    if not report["tenant_tables_present"]:
        lines.append("- None")
    lines.extend(["", "## Missing Target Tables", ""])
    lines.extend(f"- `{table}`" for table in report["missing_target_tables"])
    if not report["missing_target_tables"]:
        lines.append("- None")
    lines.extend(["", "## Global Tables Present", ""])
    lines.extend(f"- `{table}`" for table in report["global_tables_present"])
    if not report["global_tables_present"]:
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_target_preflight",
        description="Read-only P3.4.2 target schema preflight before import rehearsal.",
    )
    parser.add_argument("--plan-json", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--target-schema", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--confirm-target-preflight",
        action="store_true",
        help="Required before opening a target DB connection.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when the generated preflight report contains blockers.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_target_preflight_report(
            plan_json=args.plan_json,
            target_url=args.target_url,
            target_schema=args.target_schema,
            confirm_target_preflight=args.confirm_target_preflight,
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
