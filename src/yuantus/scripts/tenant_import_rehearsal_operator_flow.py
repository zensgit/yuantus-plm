from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_external_status as external_status
from yuantus.scripts import tenant_import_rehearsal_operator_bundle as operator_bundle
from yuantus.scripts import tenant_import_rehearsal_operator_request as operator_request
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-operator-flow-v1"


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _paths(prefix: Path) -> dict[str, Path]:
    return {
        "external_status_json": prefix.with_name(f"{prefix.name}_external_status.json"),
        "external_status_md": prefix.with_name(f"{prefix.name}_external_status.md"),
        "operator_request_json": prefix.with_name(f"{prefix.name}_operator_request.json"),
        "operator_request_md": prefix.with_name(f"{prefix.name}_operator_request.md"),
        "operator_bundle_json": prefix.with_name(f"{prefix.name}_operator_bundle.json"),
        "operator_bundle_md": prefix.with_name(f"{prefix.name}_operator_bundle.md"),
    }


def build_operator_flow_report(
    *,
    operator_packet_json: str | Path,
    artifact_prefix: str | Path,
) -> dict[str, Any]:
    """Build the DB-free external-status, request, and bundle chain."""
    output_paths = _paths(Path(artifact_prefix))

    status_report = external_status.build_external_status_report(
        operator_packet_json=operator_packet_json,
    )
    _write_json(output_paths["external_status_json"], status_report)
    _write_markdown(
        output_paths["external_status_md"],
        external_status.render_markdown_report(status_report),
    )

    request_report = operator_request.build_operator_request_report(
        external_status_json=output_paths["external_status_json"],
    )
    _write_json(output_paths["operator_request_json"], request_report)
    _write_markdown(
        output_paths["operator_request_md"],
        operator_request.render_markdown_report(request_report),
    )

    bundle_report = operator_bundle.build_operator_bundle_report(
        operator_request_json=output_paths["operator_request_json"],
    )
    _write_json(output_paths["operator_bundle_json"], bundle_report)
    _write_markdown(
        output_paths["operator_bundle_md"],
        operator_bundle.render_markdown_report(bundle_report),
    )

    blockers: list[str] = []
    if status_report.get("ready_for_external_progress") is not True:
        blockers.append("external status must have ready_for_external_progress=true")
    blockers.extend(f"external status: {item}" for item in _as_list(status_report.get("blockers")))
    if request_report.get("ready_for_operator_request") is not True:
        blockers.append("operator request must have ready_for_operator_request=true")
    blockers.extend(f"operator request: {item}" for item in _as_list(request_report.get("blockers")))
    if bundle_report.get("ready_for_operator_bundle") is not True:
        blockers.append("operator bundle must have ready_for_operator_bundle=true")
    blockers.extend(f"operator bundle: {item}" for item in _as_list(bundle_report.get("blockers")))

    return {
        "schema_version": SCHEMA_VERSION,
        "operator_packet_json": str(Path(operator_packet_json)),
        "artifact_prefix": str(Path(artifact_prefix)),
        "current_stage": status_report.get("current_stage", ""),
        "next_action": status_report.get("next_action", ""),
        "next_command_name": status_report.get("next_command_name", ""),
        "ready_for_external_progress": status_report.get("ready_for_external_progress") is True,
        "ready_for_operator_request": request_report.get("ready_for_operator_request") is True,
        "ready_for_operator_bundle": bundle_report.get("ready_for_operator_bundle") is True,
        "ready_for_operator_flow": not blockers,
        "ready_for_cutover": False,
        "outputs": {key: str(path) for key, path in output_paths.items()},
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Operator Flow",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for operator flow: `{str(report['ready_for_operator_flow']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Current stage: `{report['current_stage']}`",
        f"- Next action: `{report['next_action']}`",
        f"- Next command name: `{report['next_command_name']}`",
        f"- Operator packet JSON: `{report['operator_packet_json']}`",
        f"- Artifact prefix: `{report['artifact_prefix']}`",
        "",
        "## Readiness",
        "",
        f"- External progress: `{str(report['ready_for_external_progress']).lower()}`",
        f"- Operator request: `{str(report['ready_for_operator_request']).lower()}`",
        f"- Operator bundle: `{str(report['ready_for_operator_bundle']).lower()}`",
        "",
        "## Outputs",
        "",
        "| Artifact | Path |",
        "| --- | --- |",
    ]
    for key, path in report["outputs"].items():
        lines.append(f"| `{key}` | `{path}` |")
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This flow reads local operator-packet state and writes DB-free handoff "
            "artifacts. It does not run rehearsal commands, open database "
            "connections, accept evidence, build an archive, authorize production "
            "cutover, or enable runtime schema-per-tenant mode.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_redacting_parser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal_operator_flow",
        description="Build DB-free P3.4.2 operator status/request/bundle artifacts.",
    )
    parser.add_argument("--operator-packet-json", required=True)
    parser.add_argument("--artifact-prefix", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the full operator flow is ready.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_operator_flow_report(
            operator_packet_json=args.operator_packet_json,
            artifact_prefix=args.artifact_prefix,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), render_markdown_report(report))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_operator_flow"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
