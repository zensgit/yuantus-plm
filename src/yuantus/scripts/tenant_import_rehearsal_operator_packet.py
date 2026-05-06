from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-operator-packet-v1"
_ENV_VAR_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
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


def _validate_env_name(value: str, label: str) -> list[str]:
    if not _ENV_VAR_RE.fullmatch(value):
        return [f"{label} must be an uppercase shell environment variable name"]
    return []


def _artifact_prefix(target_schema: str, artifact_prefix: str) -> str:
    if artifact_prefix:
        return artifact_prefix.rstrip("/")
    return f"output/{target_schema}"


def _paths(prefix: str) -> dict[str, str]:
    return {
        "rehearsal_json": f"{prefix}_import_rehearsal.json",
        "rehearsal_md": f"{prefix}_import_rehearsal.md",
        "operator_evidence_template_json": (
            f"{prefix}_operator_rehearsal_evidence_template.json"
        ),
        "operator_evidence_md": f"{prefix}_operator_rehearsal_evidence.md",
        "evidence_json": f"{prefix}_import_rehearsal_evidence.json",
        "evidence_md": f"{prefix}_import_rehearsal_evidence.md",
        "archive_json": f"{prefix}_import_rehearsal_evidence_archive.json",
        "archive_md": f"{prefix}_import_rehearsal_evidence_archive.md",
    }


def _command_lines(command: list[str]) -> str:
    lines = [command[0]]
    for part in command[1:]:
        lines[-1] += " \\"
        lines.append(f"  {part}")
    return "\n".join(lines)


def _commands(
    *,
    implementation_packet_json: Path,
    paths: dict[str, str],
    source_url_env: str,
    target_url_env: str,
) -> list[dict[str, Any]]:
    row_copy = [
        "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal",
        f"--implementation-packet-json {implementation_packet_json}",
        f'--source-url "${{{source_url_env}}}"',
        f'--target-url "${{{target_url_env}}}"',
        f"--output-json {paths['rehearsal_json']}",
        f"--output-md {paths['rehearsal_md']}",
        "--confirm-rehearsal",
        "--strict",
    ]
    template = [
        "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_template",
        f"--rehearsal-json {paths['rehearsal_json']}",
        '--backup-restore-owner "<owner>"',
        '--rehearsal-window "<window>"',
        '--rehearsal-executed-by "<operator>"',
        "--rehearsal-result pass",
        '--evidence-reviewer "<reviewer>"',
        '--date "<yyyy-mm-dd>"',
        f"--output-json {paths['operator_evidence_template_json']}",
        f"--output-md {paths['operator_evidence_md']}",
        "--strict",
    ]
    evidence = [
        "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence",
        f"--rehearsal-json {paths['rehearsal_json']}",
        f"--implementation-packet-json {implementation_packet_json}",
        f"--operator-evidence-md {paths['operator_evidence_md']}",
        f"--output-json {paths['evidence_json']}",
        f"--output-md {paths['evidence_md']}",
        "--strict",
    ]
    archive = [
        "PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_archive",
        f"--evidence-json {paths['evidence_json']}",
        f"--operator-evidence-template-json {paths['operator_evidence_template_json']}",
        f"--output-json {paths['archive_json']}",
        f"--output-md {paths['archive_md']}",
        "--strict",
    ]
    return [
        {"name": "row_copy_rehearsal", "command": _command_lines(row_copy)},
        {"name": "operator_evidence_template", "command": _command_lines(template)},
        {"name": "evidence_gate", "command": _command_lines(evidence)},
        {"name": "archive_manifest", "command": _command_lines(archive)},
    ]


def build_operator_packet_report(
    *,
    implementation_packet_json: str | Path,
    artifact_prefix: str = "",
    source_url_env: str = "SOURCE_DATABASE_URL",
    target_url_env: str = "TARGET_DATABASE_URL",
) -> dict[str, Any]:
    """Build an operator execution packet without opening database connections."""
    packet_path = Path(implementation_packet_json)
    packet_report, read_error = _read_json_object(packet_path)
    blockers: list[str] = []
    if read_error:
        packet_report = {}
        blockers.append(f"implementation packet {read_error}")
    assert packet_report is not None

    blockers.extend(_validate_env_name(source_url_env, "source_url_env"))
    blockers.extend(_validate_env_name(target_url_env, "target_url_env"))

    if packet_report.get("schema_version") != packet.SCHEMA_VERSION:
        blockers.append(f"implementation packet schema_version must be {packet.SCHEMA_VERSION}")
    if packet_report.get("ready_for_claude_importer") is not True:
        blockers.append("implementation packet must have ready_for_claude_importer=true")
    if packet_report.get("ready_for_cutover") is not False:
        blockers.append("implementation packet must have ready_for_cutover=false")
    if _as_list(packet_report.get("blockers")):
        blockers.append("implementation packet must have no blockers")
    for key in _REQUIRED_PACKET_FIELDS:
        if not _as_str(packet_report.get(key)):
            blockers.append(f"implementation packet missing {key}")

    next_action_json = _as_str(packet_report.get("next_action_json"))
    if next_action_json:
        try:
            fresh_report = packet.build_implementation_packet_report(
                next_action_json,
                output_md=_as_str(packet_report.get("implementation_md"))
                or "tenant_import_rehearsal_operator_packet.md",
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

    target_schema = _as_str(packet_report.get("target_schema"))
    prefix = _artifact_prefix(target_schema, artifact_prefix)
    paths = _paths(prefix)
    return {
        "schema_version": SCHEMA_VERSION,
        "implementation_packet_json": str(packet_path),
        "implementation_packet_schema_version": packet_report.get("schema_version", ""),
        "tenant_id": _as_str(packet_report.get("tenant_id")),
        "target_schema": target_schema,
        "target_url": _as_str(packet_report.get("target_url")),
        "artifact_prefix": prefix,
        "source_url_env": source_url_env,
        "target_url_env": target_url_env,
        "ready_for_operator_execution": not blockers,
        "ready_for_cutover": False,
        "outputs": paths,
        "commands": _commands(
            implementation_packet_json=packet_path,
            paths=paths,
            source_url_env=source_url_env,
            target_url_env=target_url_env,
        ),
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Operator Packet",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for operator execution: `{str(report['ready_for_operator_execution']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Implementation packet JSON: `{report['implementation_packet_json']}`",
        f"- Artifact prefix: `{report['artifact_prefix']}`",
        f"- Source URL env: `{report['source_url_env']}`",
        f"- Target URL env: `{report['target_url_env']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Commands",
            "",
            "Run these commands in order after setting the source and target DSN "
            "environment variables. Do not paste credentials into this document.",
            "",
        ]
    )
    for command in report["commands"]:
        lines.extend(
            [
                f"### {command['name']}",
                "",
                "```bash",
                command["command"],
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Outputs",
            "",
            "| Artifact | Path |",
            "| --- | --- |",
        ]
    )
    for name, path in report["outputs"].items():
        lines.append(f"| `{name}` | `{path}` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This packet prepares operator commands for a non-production rehearsal. "
            "It does not run the commands, open database connections, or authorize "
            "production cutover.",
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
    parser = build_redacting_parser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal_operator_packet",
        description="Build DB-free operator commands for P3.4.2 tenant import rehearsal.",
    )
    parser.add_argument("--implementation-packet-json", required=True)
    parser.add_argument("--artifact-prefix", default="")
    parser.add_argument("--source-url-env", default="SOURCE_DATABASE_URL")
    parser.add_argument("--target-url-env", default="TARGET_DATABASE_URL")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the operator packet is ready for execution.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_operator_packet_report(
            implementation_packet_json=args.implementation_packet_json,
            artifact_prefix=args.artifact_prefix,
            source_url_env=args.source_url_env,
            target_url_env=args.target_url_env,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_operator_execution"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
