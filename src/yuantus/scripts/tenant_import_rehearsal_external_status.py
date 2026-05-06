from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_archive as archive
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template
from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-external-status-v1"


@dataclass(frozen=True)
class _Step:
    output_key: str
    command_name: str
    stage: str
    next_action: str
    schema_version: str | None
    ready_field: str | None
    companion_output_key: str = ""
    extra_true_fields: tuple[str, ...] = ()


_STEPS = (
    _Step(
        output_key="rehearsal_json",
        command_name="row_copy_rehearsal",
        stage="awaiting_row_copy_rehearsal",
        next_action="run_row_copy_rehearsal",
        schema_version=tenant_import_rehearsal.SCHEMA_VERSION,
        ready_field="ready_for_rehearsal_import",
        companion_output_key="rehearsal_md",
        extra_true_fields=("import_executed", "db_connection_attempted"),
    ),
    _Step(
        output_key="operator_evidence_template_json",
        command_name="operator_evidence_template",
        stage="awaiting_operator_evidence_template",
        next_action="run_operator_evidence_template",
        schema_version=template.SCHEMA_VERSION,
        ready_field="ready_for_operator_evidence_template",
        companion_output_key="operator_evidence_md",
    ),
    _Step(
        output_key="operator_evidence_md",
        command_name="operator_evidence_template",
        stage="awaiting_operator_evidence_markdown",
        next_action="write_or_generate_operator_evidence_markdown",
        schema_version=None,
        ready_field=None,
    ),
    _Step(
        output_key="evidence_json",
        command_name="evidence_gate",
        stage="awaiting_evidence_gate",
        next_action="run_evidence_gate",
        schema_version=evidence.SCHEMA_VERSION,
        ready_field="ready_for_rehearsal_evidence",
        companion_output_key="evidence_md",
        extra_true_fields=("operator_rehearsal_evidence_accepted",),
    ),
    _Step(
        output_key="archive_json",
        command_name="archive_manifest",
        stage="awaiting_archive_manifest",
        next_action="run_archive_manifest",
        schema_version=archive.SCHEMA_VERSION,
        ready_field="ready_for_archive",
        companion_output_key="archive_md",
    ),
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


def _command_by_name(report: dict[str, Any]) -> dict[str, str]:
    commands: dict[str, str] = {}
    for item in report.get("commands") or []:
        if isinstance(item, dict):
            name = _as_str(item.get("name"))
            command = _as_str(item.get("command"))
            if name and command:
                commands[name] = command
    return commands


def _validate_operator_packet(
    report: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if report.get("schema_version") != operator_packet.SCHEMA_VERSION:
        blockers.append(
            f"operator packet schema_version must be {operator_packet.SCHEMA_VERSION}"
        )
    if report.get("ready_for_operator_execution") is not True:
        blockers.append("operator packet must have ready_for_operator_execution=true")
    if report.get("ready_for_cutover") is not False:
        blockers.append("operator packet must have ready_for_cutover=false")
    if _as_list(report.get("blockers")):
        blockers.append("operator packet must have no blockers")
    outputs = report.get("outputs")
    if not isinstance(outputs, dict):
        blockers.append("operator packet outputs must be an object")
    commands = _command_by_name(report)
    for step in _STEPS:
        if step.command_name not in commands:
            blockers.append(f"operator packet missing command {step.command_name}")
    return blockers


def _json_step_status(
    *,
    step: _Step,
    path: Path,
    outputs: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    status: dict[str, Any] = {
        "artifact": step.output_key,
        "path": str(path),
        "exists": True,
        "schema_version": "",
        "ready_field": step.ready_field or "",
        "ready": False,
        "companion_path": "",
        "companion_exists": None,
    }
    payload, read_error = _read_json_object(path)
    blockers: list[str] = []
    if read_error:
        blockers.append(f"{step.output_key} {read_error}")
        return status, blockers
    assert payload is not None

    actual_schema = _as_str(payload.get("schema_version"))
    status["schema_version"] = actual_schema
    if actual_schema != step.schema_version:
        blockers.append(f"{step.output_key} schema_version must be {step.schema_version}")
    if step.ready_field and payload.get(step.ready_field) is not True:
        blockers.append(f"{step.output_key} must have {step.ready_field}=true")
    for field in step.extra_true_fields:
        if payload.get(field) is not True:
            blockers.append(f"{step.output_key} must have {field}=true")
    if payload.get("ready_for_cutover") is not False:
        blockers.append(f"{step.output_key} must have ready_for_cutover=false")
    if _as_list(payload.get("blockers")):
        blockers.append(f"{step.output_key} must have no blockers")

    if step.companion_output_key:
        companion_path = Path(_as_str(outputs.get(step.companion_output_key)))
        status["companion_path"] = str(companion_path)
        companion_exists = companion_path.is_file()
        status["companion_exists"] = companion_exists
        if not companion_exists:
            blockers.append(
                f"{step.output_key} companion {step.companion_output_key} "
                f"{companion_path} does not exist"
            )

    status["ready"] = not blockers
    return status, blockers


def _pending_status(step: _Step, path_text: str) -> dict[str, Any]:
    return {
        "artifact": step.output_key,
        "path": path_text,
        "exists": False,
        "schema_version": "",
        "ready_field": step.ready_field or "",
        "ready": False,
        "companion_path": "",
        "companion_exists": None,
    }


def _text_step_status(step: _Step, path: Path) -> tuple[dict[str, Any], list[str]]:
    status = {
        "artifact": step.output_key,
        "path": str(path),
        "exists": True,
        "schema_version": "",
        "ready_field": "",
        "ready": True,
        "companion_path": "",
        "companion_exists": None,
    }
    blockers: list[str] = []
    try:
        text = path.read_text()
    except Exception as exc:
        blockers.append(f"{step.output_key} {path} cannot be read: {exc}")
        status["ready"] = False
        return status, blockers
    if not text.strip():
        blockers.append(f"{step.output_key} must not be empty")
        status["ready"] = False
    return status, blockers


def build_external_status_report(
    *,
    operator_packet_json: str | Path,
) -> dict[str, Any]:
    """Report external P3.4 rehearsal progress without executing any command."""
    packet_path = Path(operator_packet_json)
    packet_report, packet_error = _read_json_object(packet_path)
    blockers: list[str] = []
    if packet_error:
        packet_report = {}
        blockers.append(f"operator packet {packet_error}")
    assert packet_report is not None

    blockers.extend(_validate_operator_packet(packet_report))
    outputs = packet_report.get("outputs") if isinstance(packet_report.get("outputs"), dict) else {}
    commands = _command_by_name(packet_report)
    artifacts: list[dict[str, Any]] = []
    first_missing: _Step | None = None

    if not blockers:
        for step in _STEPS:
            path_text = _as_str(outputs.get(step.output_key))
            if not path_text:
                blockers.append(f"operator packet outputs missing {step.output_key}")
                artifacts.append(_pending_status(step, ""))
                continue
            path = Path(path_text)
            if not path.is_file():
                if first_missing is None:
                    first_missing = step
                artifacts.append(_pending_status(step, path_text))
                continue
            if first_missing is not None:
                blockers.append(
                    f"{step.output_key} exists before {first_missing.output_key}"
                )
            if step.schema_version is None:
                status, step_blockers = _text_step_status(step, path)
            else:
                status, step_blockers = _json_step_status(
                    step=step,
                    path=path,
                    outputs=outputs,
                )
            artifacts.append(status)
            blockers.extend(step_blockers)

    if blockers:
        current_stage = "blocked_external_status"
        next_action = "fix_blockers"
        next_command_name = ""
        next_command = ""
    elif first_missing is not None:
        current_stage = first_missing.stage
        next_action = first_missing.next_action
        next_command_name = first_missing.command_name
        next_command = commands.get(first_missing.command_name, "")
    else:
        current_stage = "rehearsal_archive_ready"
        next_action = "review_archive_and_hold_cutover_gate"
        next_command_name = ""
        next_command = ""

    return {
        "schema_version": SCHEMA_VERSION,
        "operator_packet_json": str(packet_path),
        "operator_packet_schema_version": packet_report.get("schema_version", ""),
        "tenant_id": _as_str(packet_report.get("tenant_id")),
        "target_schema": _as_str(packet_report.get("target_schema")),
        "target_url": _as_str(packet_report.get("target_url")),
        "current_stage": current_stage,
        "next_action": next_action,
        "next_command_name": next_command_name,
        "next_command": next_command,
        "ready_for_external_progress": not blockers,
        "ready_for_cutover": False,
        "artifacts": artifacts,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal External Status",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Current stage: `{report['current_stage']}`",
        f"- Next action: `{report['next_action']}`",
        f"- Ready for external progress: `{str(report['ready_for_external_progress']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Operator packet JSON: `{report['operator_packet_json']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Next Command",
            "",
        ]
    )
    if report["next_command"]:
        lines.extend(["```bash", report["next_command"], "```", ""])
    else:
        lines.extend(["None", ""])
    lines.extend(
        [
            "## Artifact Status",
            "",
            "| Artifact | Exists | Ready | Schema version | Companion exists | Path |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for artifact in report["artifacts"]:
        companion = artifact["companion_exists"]
        companion_text = "n/a" if companion is None else str(companion).lower()
        lines.append(
            "| "
            f"`{artifact['artifact']}` | "
            f"`{str(artifact['exists']).lower()}` | "
            f"`{str(artifact['ready']).lower()}` | "
            f"`{artifact['schema_version']}` | "
            f"`{companion_text}` | "
            f"`{artifact['path']}` |"
        )
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This status report reads existing files only. It does not run row-copy, "
            "open database connections, accept evidence, build an archive, or "
            "authorize cutover.",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_external_status",
        description="Report DB-free P3.4.2 external rehearsal progress.",
    )
    parser.add_argument("--operator-packet-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when existing artifacts are invalid or the packet is blocked.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_external_status_report(
            operator_packet_json=args.operator_packet_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_external_progress"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
