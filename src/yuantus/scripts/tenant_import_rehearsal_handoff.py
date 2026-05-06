from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser
from yuantus.scripts.tenant_import_rehearsal_readiness import (
    SCHEMA_VERSION as READINESS_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_migration_dry_run import SCHEMA_VERSION as DRY_RUN_SCHEMA_VERSION


SCHEMA_VERSION = "p3.4.2-claude-import-rehearsal-handoff-v1"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _checks(readiness: dict[str, Any]) -> dict[str, Any]:
    value = readiness.get("checks")
    return value if isinstance(value, dict) else {}


def _blockers(readiness: dict[str, Any]) -> list[str]:
    value = readiness.get("blockers")
    if isinstance(value, list):
        return [str(item) for item in value]
    return ["readiness blockers must be a list"]


def build_handoff_report(readiness_json: str | Path, handoff_md: str | Path) -> dict[str, Any]:
    """Decide whether Claude can start the importer implementation."""
    readiness_path = Path(readiness_json)
    handoff_path = Path(handoff_md)
    readiness = _read_json(readiness_path)
    checks = _checks(readiness)

    blockers: list[str] = []
    if readiness.get("schema_version") != READINESS_SCHEMA_VERSION:
        blockers.append(f"readiness schema_version must be {READINESS_SCHEMA_VERSION}")
    if readiness.get("dry_run_schema_version") != DRY_RUN_SCHEMA_VERSION:
        blockers.append(f"dry_run_schema_version must be {DRY_RUN_SCHEMA_VERSION}")
    if readiness.get("ready_for_import") is not True:
        blockers.append("readiness report must have ready_for_import=true")
    if readiness.get("ready_for_rehearsal") is not True:
        blockers.append("readiness report must have ready_for_rehearsal=true")
    if _blockers(readiness):
        blockers.append("readiness report must have no blockers")
    if not _as_str(readiness.get("tenant_id")):
        blockers.append("readiness report missing tenant_id")
    if not _as_str(readiness.get("target_schema")):
        blockers.append("readiness report missing target_schema")
    if not _as_str(readiness.get("target_url")):
        blockers.append("readiness report missing redacted target_url")
    if not _as_str(checks.get("dry_run_json")):
        blockers.append("readiness checks missing dry_run_json")

    return {
        "schema_version": SCHEMA_VERSION,
        "readiness_json": str(readiness_path),
        "readiness_schema_version": readiness.get("schema_version"),
        "tenant_id": _as_str(readiness.get("tenant_id")),
        "target_schema": _as_str(readiness.get("target_schema")),
        "target_url": _as_str(readiness.get("target_url")),
        "dry_run_json": _as_str(checks.get("dry_run_json")),
        "backup_restore_owner": _as_str(checks.get("backup_restore_owner")),
        "rehearsal_window": _as_str(checks.get("rehearsal_window")),
        "classification_artifact": _as_str(checks.get("classification_artifact")),
        "handoff_md": str(handoff_path),
        "ready_for_claude": not blockers,
        "blockers": blockers,
    }


def render_handoff_markdown(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    ready = str(report["ready_for_claude"]).lower()
    lines = [
        "# Claude Task — P3.4.2 Tenant Import Rehearsal Implementation",
        "",
        f"- Handoff schema: `{report['schema_version']}`",
        f"- Claude can start: `{ready}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Readiness JSON: `{report['readiness_json']}`",
        f"- Dry-run JSON: `{report['dry_run_json']}`",
        f"- Backup/restore owner: `{report['backup_restore_owner']}`",
        f"- Rehearsal window: `{report['rehearsal_window']}`",
        f"- Classification artifact: `{report['classification_artifact']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Implementation Scope",
            "",
            "Implement `yuantus.scripts.tenant_import_rehearsal` only when "
            "`Claude can start` is `true`.",
            "",
            "The importer must:",
            "",
            "- require `--confirm-rehearsal` before any DB connection;",
            "- require `--readiness-json` and validate this handoff's readiness report "
            "before any DB connection;",
            "- validate the P3.4.1 dry-run JSON before connecting;",
            "- connect to the source DB read-only;",
            "- connect only to the non-production PostgreSQL target DSN supplied by the operator;",
            "- assert the target schema exists and has `t1_initial_tenant_baseline`;",
            "- import only tables from `tenant_tables_in_import_order`;",
            "- block every global/control-plane table;",
            "- emit JSON and Markdown rehearsal reports;",
            "- keep `ready_for_cutover=false`.",
            "",
            "## Non-Goals",
            "",
            "- No production cutover.",
            "- No `TENANCY_MODE=schema-per-tenant` enablement.",
            "- No source writes.",
            "- No global/control-plane table import.",
            "- No schema creation or migration.",
            "- No automatic rollback or destructive cleanup.",
            "",
            "## Required Verification",
            "",
            "```bash",
            ".venv/bin/python -m pytest -q \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal.py \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \\",
            "  src/yuantus/tests/test_tenant_migration_dry_run.py",
            "",
            ".venv/bin/python -m py_compile \\",
            "  src/yuantus/scripts/tenant_import_rehearsal.py \\",
            "  src/yuantus/scripts/tenant_import_rehearsal_handoff.py",
            "",
            "git diff --check",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_handoff_markdown(report))


def main(argv: list[str] | None = None) -> int:
    parser = build_redacting_parser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal_handoff",
        description="Generate a Claude handoff only after P3.4.2 readiness is true.",
    )
    parser.add_argument("--readiness-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when Claude handoff blockers are present.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_handoff_report(args.readiness_json, args.output_md)
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
