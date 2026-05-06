from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_archive as archive
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template
from yuantus.scripts import tenant_import_rehearsal_operator_packet as operator_packet
from yuantus.scripts import tenant_import_rehearsal_redaction_guard as redaction_guard
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-evidence-intake-v1"
_REQUIRED_OUTPUTS = (
    "rehearsal_json",
    "rehearsal_md",
    "operator_evidence_template_json",
    "operator_evidence_md",
    "evidence_json",
    "evidence_md",
    "archive_json",
    "archive_md",
)
_JSON_SCHEMAS = {
    "rehearsal_json": tenant_import_rehearsal.SCHEMA_VERSION,
    "operator_evidence_template_json": template.SCHEMA_VERSION,
    "evidence_json": evidence.SCHEMA_VERSION,
    "archive_json": archive.SCHEMA_VERSION,
}
_READY_FIELDS = {
    "rehearsal_json": "ready_for_rehearsal_import",
    "operator_evidence_template_json": "ready_for_operator_evidence_template",
    "evidence_json": "ready_for_rehearsal_evidence",
    "archive_json": "ready_for_archive",
}
_EXTRA_TRUE_FIELDS = {
    "rehearsal_json": ("import_executed", "db_connection_attempted"),
    "evidence_json": ("operator_rehearsal_evidence_accepted",),
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


def _artifact_status(*, key: str, path_text: str) -> tuple[dict[str, Any], list[str]]:
    path = Path(path_text)
    status: dict[str, Any] = {
        "artifact": key,
        "path": path_text,
        "exists": path.is_file(),
        "readable": False,
        "schema_version": "",
        "ready_field": _READY_FIELDS.get(key, ""),
        "ready": False,
        "synthetic_drill": False,
    }
    blockers: list[str] = []
    if not path.is_file():
        blockers.append(f"{key} {path_text} does not exist")
        return status, blockers

    if key.endswith("_md"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            blockers.append(f"{key} {path_text} cannot be read: {exc}")
            return status, blockers
        status["readable"] = True
        if not text.strip():
            blockers.append(f"{key} must not be empty")
        if "Synthetic drill: `true`" in text or "Real rehearsal evidence: `false`" in text:
            status["synthetic_drill"] = True
            blockers.append(f"{key} must not be synthetic drill output")
        status["ready"] = not blockers
        return status, blockers

    payload, read_error = _read_json_object(path)
    if read_error:
        blockers.append(f"{key} {read_error}")
        return status, blockers
    assert payload is not None
    status["readable"] = True
    status["schema_version"] = _as_str(payload.get("schema_version"))
    status["synthetic_drill"] = payload.get("synthetic_drill") is True

    expected_schema = _JSON_SCHEMAS.get(key)
    if expected_schema and payload.get("schema_version") != expected_schema:
        blockers.append(f"{key} schema_version must be {expected_schema}")
    ready_field = _READY_FIELDS.get(key)
    if ready_field and payload.get(ready_field) is not True:
        blockers.append(f"{key} must have {ready_field}=true")
    for field in _EXTRA_TRUE_FIELDS.get(key, ()):
        if payload.get(field) is not True:
            blockers.append(f"{key} must have {field}=true")
    if payload.get("ready_for_cutover") is not False:
        blockers.append(f"{key} must have ready_for_cutover=false")
    if _as_list(payload.get("blockers")):
        blockers.append(f"{key} must have no blockers")
    if payload.get("synthetic_drill") is True or payload.get(
        "real_rehearsal_evidence"
    ) is False:
        blockers.append(f"{key} must not be synthetic drill output")

    status["ready"] = not blockers
    return status, blockers


def build_evidence_intake_report(*, operator_packet_json: str | Path) -> dict[str, Any]:
    """Validate the completed P3.4 evidence artifact set without DB access."""
    packet_path = Path(operator_packet_json)
    packet_report, packet_error = _read_json_object(packet_path)
    blockers: list[str] = []
    if packet_error:
        packet_report = {}
        blockers.append(f"operator packet {packet_error}")
    assert packet_report is not None

    if packet_report.get("schema_version") != operator_packet.SCHEMA_VERSION:
        blockers.append(
            f"operator packet schema_version must be {operator_packet.SCHEMA_VERSION}"
        )
    if packet_report.get("ready_for_operator_execution") is not True:
        blockers.append("operator packet must have ready_for_operator_execution=true")
    if packet_report.get("ready_for_cutover") is not False:
        blockers.append("operator packet must have ready_for_cutover=false")
    if _as_list(packet_report.get("blockers")):
        blockers.append("operator packet must have no blockers")

    outputs = packet_report.get("outputs")
    if not isinstance(outputs, dict):
        outputs = {}
        blockers.append("operator packet outputs must be an object")

    artifact_statuses: list[dict[str, Any]] = []
    scan_paths: list[Path] = []
    for key in _REQUIRED_OUTPUTS:
        path_text = _as_str(outputs.get(key))
        if not path_text:
            blockers.append(f"operator packet outputs missing {key}")
            artifact_statuses.append(
                {
                    "artifact": key,
                    "path": "",
                    "exists": False,
                    "readable": False,
                    "schema_version": "",
                    "ready_field": _READY_FIELDS.get(key, ""),
                    "ready": False,
                    "synthetic_drill": False,
                }
            )
            continue
        status, status_blockers = _artifact_status(key=key, path_text=path_text)
        artifact_statuses.append(status)
        blockers.extend(status_blockers)
        if status["exists"]:
            scan_paths.append(Path(path_text))

    redaction_report = redaction_guard.build_redaction_guard_report(
        artifacts=scan_paths,
    )
    redaction_ready = redaction_report["ready_for_artifact_handoff"]
    if not redaction_ready:
        blockers.append("redaction scan must be clean before evidence intake")
    blockers.extend(redaction_report["blockers"])

    return {
        "schema_version": SCHEMA_VERSION,
        "operator_packet_json": str(packet_path),
        "operator_packet_schema_version": packet_report.get("schema_version", ""),
        "tenant_id": _as_str(packet_report.get("tenant_id")),
        "target_schema": _as_str(packet_report.get("target_schema")),
        "target_url": _as_str(packet_report.get("target_url")),
        "artifact_count": len(artifact_statuses),
        "artifacts": artifact_statuses,
        "redaction_artifact_count": redaction_report["artifact_count"],
        "redaction_ready": redaction_ready,
        "ready_for_evidence_intake": not blockers,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Evidence Intake",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for evidence intake: `{str(report['ready_for_evidence_intake']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Operator packet JSON: `{report['operator_packet_json']}`",
        f"- Artifact count: `{report['artifact_count']}`",
        f"- Redaction artifact count: `{report['redaction_artifact_count']}`",
        f"- Redaction ready: `{str(report['redaction_ready']).lower()}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Artifact Status",
            "",
            "| Artifact | Exists | Readable | Schema | Ready | Synthetic | Path |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in report["artifacts"]:
        lines.append(
            "| "
            f"`{item['artifact']}` | "
            f"`{str(item['exists']).lower()}` | "
            f"`{str(item['readable']).lower()}` | "
            f"`{item['schema_version']}` | "
            f"`{str(item['ready']).lower()}` | "
            f"`{str(item['synthetic_drill']).lower()}` | "
            f"`{item['path']}` |"
        )
    if not report["artifacts"]:
        lines.append("| None | `false` | `false` | `` | `false` | `false` | `` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This intake checklist reads local artifacts only. It does not open "
            "database connections, run rehearsal commands, accept evidence, build "
            "an archive, run the evidence handoff gate, authorize production "
            "cutover, or enable runtime schema-per-tenant mode.",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_evidence_intake",
        description=(
            "Validate completed P3.4.2 evidence artifacts before reviewer intake."
        ),
    )
    parser.add_argument("--operator-packet-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the evidence artifact set is intake-ready.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_evidence_intake_report(
            operator_packet_json=args.operator_packet_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_evidence_intake"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
