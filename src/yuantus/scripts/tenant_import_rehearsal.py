from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-scaffold-v1"
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


def build_rehearsal_scaffold_report(
    implementation_packet_json: str | Path,
    *,
    confirm_rehearsal: bool,
) -> dict[str, Any]:
    """Validate importer prerequisites without connecting to any database."""
    packet_path = Path(implementation_packet_json)
    packet_report, packet_blockers, fresh_report = _validate_packet(packet_path)
    blockers = list(packet_blockers)
    if not confirm_rehearsal:
        blockers.insert(0, "missing --confirm-rehearsal")
    ready = not blockers

    return {
        "schema_version": SCHEMA_VERSION,
        "implementation_packet_json": str(packet_path),
        "implementation_packet_schema_version": packet_report.get("schema_version", ""),
        "ready_for_rehearsal_scaffold": ready,
        "ready_for_import_execution": ready,
        "import_executed": False,
        "db_connection_attempted": False,
        "ready_for_cutover": False,
        "tenant_id": _as_str(packet_report.get("tenant_id")),
        "target_schema": _as_str(packet_report.get("target_schema")),
        "target_url": _as_str(packet_report.get("target_url")),
        "next_action_json": _as_str(packet_report.get("next_action_json")),
        "dry_run_json": _as_str(packet_report.get("dry_run_json")),
        "readiness_json": _as_str(packet_report.get("readiness_json")),
        "handoff_json": _as_str(packet_report.get("handoff_json")),
        "plan_json": _as_str(packet_report.get("plan_json")),
        "source_preflight_json": _as_str(packet_report.get("source_preflight_json")),
        "target_preflight_json": _as_str(packet_report.get("target_preflight_json")),
        "fresh_artifact_validations": fresh_report.get("artifact_validations", []),
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    validations = report.get("fresh_artifact_validations") or []
    lines = [
        "# Tenant Import Rehearsal Scaffold Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Scaffold guard passed: `{str(report['ready_for_rehearsal_scaffold']).lower()}`",
        f"- Import executed: `{str(report['import_executed']).lower()}`",
        f"- DB connection attempted: `{str(report['db_connection_attempted']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
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
            "## Scope",
            "",
            "This scaffold stops before any source or target database connection. "
            "A later importer PR must add the row-copy implementation behind "
            "the same guards.",
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
        description="Validate P3.4.2 tenant import rehearsal guards without importing rows.",
    )
    parser.add_argument("--implementation-packet-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--confirm-rehearsal", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the scaffold guard passes.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_rehearsal_scaffold_report(
            args.implementation_packet_json,
            confirm_rehearsal=args.confirm_rehearsal,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_rehearsal_scaffold"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
