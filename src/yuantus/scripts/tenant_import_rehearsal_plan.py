from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts.tenant_import_rehearsal_handoff import (
    SCHEMA_VERSION as HANDOFF_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_migration_dry_run import (
    BASELINE_REVISION,
    SCHEMA_VERSION as DRY_RUN_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_schema import GLOBAL_TABLE_NAMES


SCHEMA_VERSION = "p3.4.2-import-rehearsal-plan-v1"


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


def _as_int_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        if isinstance(key, str) and isinstance(count, int):
            result[key] = count
    return result


def _list_blockers(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def build_import_plan_report(
    *,
    dry_run_json: str | Path,
    handoff_json: str | Path,
) -> dict[str, Any]:
    dry_run_path = Path(dry_run_json)
    handoff_path = Path(handoff_json)
    dry_run = _read_json(dry_run_path)
    handoff = _read_json(handoff_path)

    import_order = _as_str_list(dry_run.get("tenant_tables_in_import_order"))
    row_counts = _as_int_map(dry_run.get("row_counts"))
    skipped_global_tables = _as_str_list(dry_run.get("excluded_global_tables_present"))

    blockers: list[str] = []
    if dry_run.get("schema_version") != DRY_RUN_SCHEMA_VERSION:
        blockers.append(f"dry-run schema_version must be {DRY_RUN_SCHEMA_VERSION}")
    if handoff.get("schema_version") != HANDOFF_SCHEMA_VERSION:
        blockers.append(f"handoff schema_version must be {HANDOFF_SCHEMA_VERSION}")
    if dry_run.get("ready_for_import") is not True:
        blockers.append("dry-run report must have ready_for_import=true")
    if handoff.get("ready_for_claude") is not True:
        blockers.append("handoff report must have ready_for_claude=true")
    if _list_blockers(dry_run.get("blockers")):
        blockers.append("dry-run report must have no blockers")
    if _list_blockers(handoff.get("blockers")):
        blockers.append("handoff report must have no blockers")
    if dry_run.get("baseline_revision") != BASELINE_REVISION:
        blockers.append(f"dry-run baseline_revision must be {BASELINE_REVISION}")
    if dry_run.get("tenant_id") != handoff.get("tenant_id"):
        blockers.append("tenant_id must match handoff")
    if dry_run.get("target_schema") != handoff.get("target_schema"):
        blockers.append("target_schema must match handoff")
    if not import_order:
        blockers.append("tenant_tables_in_import_order must be a non-empty list")

    global_tables_in_plan = sorted(set(import_order) & set(GLOBAL_TABLE_NAMES))
    if global_tables_in_plan:
        blockers.append(
            "import plan includes global/control-plane tables: "
            + ", ".join(global_tables_in_plan)
        )

    import_order_set = set(import_order)
    row_count_names = set(row_counts)
    missing_row_counts = sorted(import_order_set - row_count_names)
    extra_row_counts = sorted(row_count_names - import_order_set)
    if missing_row_counts:
        blockers.append(
            "row_counts missing import tables: "
            + ", ".join(missing_row_counts[:10])
            + ("..." if len(missing_row_counts) > 10 else "")
        )
    if extra_row_counts:
        blockers.append(
            "row_counts contains tables outside import order: "
            + ", ".join(extra_row_counts[:10])
            + ("..." if len(extra_row_counts) > 10 else "")
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "dry_run_json": str(dry_run_path),
        "handoff_json": str(handoff_path),
        "tenant_id": _as_str(dry_run.get("tenant_id")),
        "target_schema": _as_str(dry_run.get("target_schema")),
        "source_url": _as_str(dry_run.get("source_url")),
        "target_url": _as_str(handoff.get("target_url")),
        "baseline_revision": _as_str(dry_run.get("baseline_revision")),
        "tenant_tables_in_import_order": import_order,
        "table_count": len(import_order),
        "source_row_counts": row_counts,
        "skipped_global_tables": skipped_global_tables,
        "ready_for_importer": not blockers,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Plan",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for importer: `{str(report['ready_for_importer']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Source URL: `{report['source_url']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Baseline revision: `{report['baseline_revision']}`",
        f"- Table count: `{report['table_count']}`",
        f"- Dry-run JSON: `{report['dry_run_json']}`",
        f"- Handoff JSON: `{report['handoff_json']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(["", "## Import Order", ""])
    lines.extend(
        f"{index}. `{table}`"
        for index, table in enumerate(report["tenant_tables_in_import_order"], 1)
    )
    if not report["tenant_tables_in_import_order"]:
        lines.append("- None")
    lines.extend(["", "## Source Row Counts", ""])
    for table in report["tenant_tables_in_import_order"]:
        count = report["source_row_counts"].get(table, "missing")
        lines.append(f"- `{table}`: {count}")
    if not report["tenant_tables_in_import_order"]:
        lines.append("- None")
    lines.extend(["", "## Skipped Global Tables", ""])
    lines.extend(f"- `{table}`" for table in report["skipped_global_tables"])
    if not report["skipped_global_tables"]:
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_plan",
        description="Build a DB-free P3.4.2 tenant import rehearsal plan manifest.",
    )
    parser.add_argument("--dry-run-json", required=True)
    parser.add_argument("--handoff-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when the generated import plan has blockers.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_import_plan_report(
            dry_run_json=args.dry_run_json,
            handoff_json=args.handoff_json,
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
