from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_external_status as external_status
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-operator-request-v1"

_STAGE_INPUTS: dict[str, list[str]] = {
    "awaiting_row_copy_rehearsal": [
        "SOURCE_DATABASE_URL environment variable",
        "TARGET_DATABASE_URL environment variable",
        "operator confirmation that the target is non-production",
    ],
    "awaiting_operator_evidence_template": [
        "backup/restore owner",
        "rehearsal window",
        "rehearsal executed by",
        "evidence reviewer",
        "evidence date",
    ],
    "awaiting_operator_evidence_markdown": [
        "completed operator evidence Markdown",
    ],
    "awaiting_evidence_gate": [
        "reviewed operator evidence Markdown",
    ],
    "awaiting_archive_manifest": [
        "accepted evidence gate JSON",
    ],
    "rehearsal_archive_ready": [
        "operator review of archive manifest",
        "hold production cutover gate",
    ],
}


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


def _artifact_summary(status_report: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for item in status_report.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        artifacts.append(
            {
                "artifact": _as_str(item.get("artifact")),
                "path": _as_str(item.get("path")),
                "exists": item.get("exists") is True,
                "ready": item.get("ready") is True,
            }
        )
    return artifacts


def build_operator_request_report(
    *,
    external_status_json: str | Path,
) -> dict[str, Any]:
    """Convert a green/pending external status report into an operator request."""
    status_path = Path(external_status_json)
    status_report, read_error = _read_json_object(status_path)
    blockers: list[str] = []
    if read_error:
        status_report = {}
        blockers.append(f"external status {read_error}")
    assert status_report is not None

    current_stage = _as_str(status_report.get("current_stage"))
    next_action = _as_str(status_report.get("next_action"))
    next_command_name = _as_str(status_report.get("next_command_name"))
    next_command = _as_str(status_report.get("next_command"))

    if status_report.get("schema_version") != external_status.SCHEMA_VERSION:
        blockers.append(
            f"external status schema_version must be {external_status.SCHEMA_VERSION}"
        )
    if status_report.get("ready_for_external_progress") is not True:
        blockers.append("external status must have ready_for_external_progress=true")
    if status_report.get("ready_for_cutover") is not False:
        blockers.append("external status must have ready_for_cutover=false")
    if _as_list(status_report.get("blockers")):
        blockers.append("external status must have no blockers")
    if current_stage not in _STAGE_INPUTS:
        blockers.append(f"external status current_stage is unsupported: {current_stage}")
    if current_stage != "rehearsal_archive_ready" and not next_command:
        blockers.append("external status must provide next_command before archive ready")

    return {
        "schema_version": SCHEMA_VERSION,
        "external_status_json": str(status_path),
        "external_status_schema_version": status_report.get("schema_version", ""),
        "tenant_id": _as_str(status_report.get("tenant_id")),
        "target_schema": _as_str(status_report.get("target_schema")),
        "target_url": _as_str(status_report.get("target_url")),
        "current_stage": current_stage,
        "next_action": next_action,
        "next_command_name": next_command_name,
        "next_command": next_command,
        "required_operator_inputs": _STAGE_INPUTS.get(current_stage, []),
        "artifacts": _artifact_summary(status_report),
        "ready_for_operator_request": not blockers,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    required_inputs = report["required_operator_inputs"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Operator Request",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for operator request: `{str(report['ready_for_operator_request']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Current stage: `{report['current_stage']}`",
        f"- Next action: `{report['next_action']}`",
        f"- Next command name: `{report['next_command_name']}`",
        f"- External status JSON: `{report['external_status_json']}`",
        "",
        "## Required Operator Inputs",
        "",
    ]
    lines.extend(f"- {item}" for item in required_inputs)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(["", "## Next Command", ""])
    if report["next_command"]:
        lines.extend(["```bash", report["next_command"], "```", ""])
    else:
        lines.extend(["None", ""])
    lines.extend(
        [
            "## Artifact Summary",
            "",
            "| Artifact | Exists | Ready | Path |",
            "| --- | --- | --- | --- |",
        ]
    )
    for artifact in report["artifacts"]:
        lines.append(
            "| "
            f"`{artifact['artifact']}` | "
            f"`{str(artifact['exists']).lower()}` | "
            f"`{str(artifact['ready']).lower()}` | "
            f"`{artifact['path']}` |"
        )
    if not report["artifacts"]:
        lines.append("| None | `false` | `false` | `` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This request reads a previously generated external status report only. "
            "It does not run commands, open database connections, accept evidence, "
            "build an archive, authorize production cutover, or enable runtime "
            "schema-per-tenant mode.",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_operator_request",
        description="Build a DB-free P3.4.2 operator request from external status.",
    )
    parser.add_argument("--external-status-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the operator request is ready.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_operator_request_report(
            external_status_json=args.external_status_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_operator_request"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
