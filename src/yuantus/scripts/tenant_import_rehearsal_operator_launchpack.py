from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_operator_flow as operator_flow
from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-operator-launchpack-v1"


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


def _default_flow_prefix(operator_packet_path: Path) -> Path:
    name = operator_packet_path.name
    if name.endswith("_operator_execution_packet.json"):
        return operator_packet_path.with_name(name.removesuffix("_operator_execution_packet.json"))
    if name.endswith(".json"):
        return operator_packet_path.with_name(name.removesuffix(".json"))
    return operator_packet_path


def build_operator_launchpack_report(
    *,
    implementation_packet_json: str | Path,
    artifact_prefix: str,
    operator_packet_json: str | Path,
    operator_packet_md: str | Path,
    flow_artifact_prefix: str | Path = "",
    source_url_env: str = "SOURCE_DATABASE_URL",
    target_url_env: str = "TARGET_DATABASE_URL",
) -> dict[str, Any]:
    """Build operator packet plus DB-free flow artifacts from implementation packet."""
    packet_json_path = Path(operator_packet_json)
    packet_md_path = Path(operator_packet_md)
    packet_report = operator_packet.build_operator_packet_report(
        implementation_packet_json=implementation_packet_json,
        artifact_prefix=artifact_prefix,
        source_url_env=source_url_env,
        target_url_env=target_url_env,
    )
    _write_json(packet_json_path, packet_report)
    _write_markdown(packet_md_path, operator_packet.render_markdown_report(packet_report))

    flow_prefix = Path(flow_artifact_prefix) if flow_artifact_prefix else _default_flow_prefix(packet_json_path)
    flow_report = operator_flow.build_operator_flow_report(
        operator_packet_json=packet_json_path,
        artifact_prefix=flow_prefix,
    )

    blockers: list[str] = []
    if packet_report.get("ready_for_operator_execution") is not True:
        blockers.append("operator packet must have ready_for_operator_execution=true")
    blockers.extend(f"operator packet: {item}" for item in _as_list(packet_report.get("blockers")))
    if flow_report.get("ready_for_operator_flow") is not True:
        blockers.append("operator flow must have ready_for_operator_flow=true")
    blockers.extend(f"operator flow: {item}" for item in _as_list(flow_report.get("blockers")))

    outputs = {
        "operator_packet_json": str(packet_json_path),
        "operator_packet_md": str(packet_md_path),
        **flow_report["outputs"],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "implementation_packet_json": str(Path(implementation_packet_json)),
        "artifact_prefix": artifact_prefix,
        "flow_artifact_prefix": str(flow_prefix),
        "ready_for_operator_packet": packet_report.get("ready_for_operator_execution") is True,
        "ready_for_operator_flow": flow_report.get("ready_for_operator_flow") is True,
        "ready_for_operator_launchpack": not blockers,
        "ready_for_cutover": False,
        "current_stage": flow_report.get("current_stage", ""),
        "next_action": flow_report.get("next_action", ""),
        "next_command_name": flow_report.get("next_command_name", ""),
        "outputs": outputs,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Operator Launchpack",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for operator launchpack: `{str(report['ready_for_operator_launchpack']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Current stage: `{report['current_stage']}`",
        f"- Next action: `{report['next_action']}`",
        f"- Next command name: `{report['next_command_name']}`",
        f"- Implementation packet JSON: `{report['implementation_packet_json']}`",
        f"- Artifact prefix: `{report['artifact_prefix']}`",
        f"- Flow artifact prefix: `{report['flow_artifact_prefix']}`",
        "",
        "## Readiness",
        "",
        f"- Operator packet: `{str(report['ready_for_operator_packet']).lower()}`",
        f"- Operator flow: `{str(report['ready_for_operator_flow']).lower()}`",
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
            "This launchpack reads the implementation packet and writes DB-free "
            "operator handoff artifacts. It does not run rehearsal commands, open "
            "database connections, accept evidence, build an archive, authorize "
            "production cutover, or enable runtime schema-per-tenant mode.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_redacting_parser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal_operator_launchpack",
        description="Build DB-free P3.4.2 operator packet and flow artifacts.",
    )
    parser.add_argument("--implementation-packet-json", required=True)
    parser.add_argument("--artifact-prefix", required=True)
    parser.add_argument("--operator-packet-json", required=True)
    parser.add_argument("--operator-packet-md", required=True)
    parser.add_argument("--flow-artifact-prefix", default="")
    parser.add_argument("--source-url-env", default="SOURCE_DATABASE_URL")
    parser.add_argument("--target-url-env", default="TARGET_DATABASE_URL")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the operator launchpack is ready.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_operator_launchpack_report(
            implementation_packet_json=args.implementation_packet_json,
            artifact_prefix=args.artifact_prefix,
            operator_packet_json=args.operator_packet_json,
            operator_packet_md=args.operator_packet_md,
            flow_artifact_prefix=args.flow_artifact_prefix,
            source_url_env=args.source_url_env,
            target_url_env=args.target_url_env,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), render_markdown_report(report))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_operator_launchpack"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
