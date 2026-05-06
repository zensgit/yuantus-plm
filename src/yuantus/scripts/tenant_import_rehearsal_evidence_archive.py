from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_evidence as evidence
from yuantus.scripts import tenant_import_rehearsal_evidence_template as template
from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts import tenant_import_rehearsal_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_next_action as next_action
from yuantus.scripts import tenant_import_rehearsal_plan as import_plan
from yuantus.scripts import tenant_import_rehearsal_readiness as readiness
from yuantus.scripts import tenant_import_rehearsal_source_preflight as source_preflight
from yuantus.scripts import tenant_import_rehearsal_target_preflight as target_preflight
from yuantus.scripts import tenant_migration_dry_run as dry_run
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-evidence-archive-v1"
_JSON_ARTIFACT_SCHEMAS = {
    "dry_run_json": dry_run.SCHEMA_VERSION,
    "readiness_json": readiness.SCHEMA_VERSION,
    "handoff_json": handoff.SCHEMA_VERSION,
    "plan_json": import_plan.SCHEMA_VERSION,
    "source_preflight_json": source_preflight.SCHEMA_VERSION,
    "target_preflight_json": target_preflight.SCHEMA_VERSION,
    "next_action_json": next_action.SCHEMA_VERSION,
    "implementation_packet_json": packet.SCHEMA_VERSION,
    "rehearsal_json": tenant_import_rehearsal.SCHEMA_VERSION,
    "evidence_json": evidence.SCHEMA_VERSION,
    "operator_evidence_template_json": template.SCHEMA_VERSION,
}
_READY_FIELDS = {
    "dry_run_json": "ready_for_import",
    "readiness_json": "ready_for_rehearsal",
    "handoff_json": "ready_for_claude",
    "plan_json": "ready_for_importer",
    "source_preflight_json": "ready_for_importer_source",
    "target_preflight_json": "ready_for_importer_target",
    "next_action_json": "claude_required",
    "implementation_packet_json": "ready_for_claude_importer",
    "rehearsal_json": "ready_for_rehearsal_import",
    "evidence_json": "ready_for_rehearsal_evidence",
    "operator_evidence_template_json": "ready_for_operator_evidence_template",
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


def _same_path(left: str, right: str | Path) -> bool:
    left_path = Path(left)
    right_path = Path(right)
    try:
        if left_path.exists() and right_path.exists():
            return left_path.resolve() == right_path.resolve()
    except OSError:
        pass
    return str(left_path) == str(right_path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_entry(
    *,
    name: str,
    path_text: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
    path = Path(path_text)
    entry: dict[str, Any] = {
        "artifact": name,
        "path": path_text,
        "exists": path.is_file(),
        "bytes": 0,
        "sha256": "",
        "schema_version": "",
        "ready_field": _READY_FIELDS.get(name, ""),
        "ready": False,
    }
    blockers: list[str] = []
    payload: dict[str, Any] | None = None
    if not path.is_file():
        blockers.append(f"{name} {path_text} does not exist")
        return entry, None, blockers

    entry["bytes"] = path.stat().st_size
    entry["sha256"] = _sha256(path)
    if name.endswith("_json"):
        payload, read_error = _read_json_object(path)
        if read_error:
            blockers.append(f"{name} {read_error}")
            return entry, None, blockers
        assert payload is not None
        entry["schema_version"] = _as_str(payload.get("schema_version"))
        expected_schema = _JSON_ARTIFACT_SCHEMAS.get(name, "")
        if expected_schema and payload.get("schema_version") != expected_schema:
            blockers.append(f"{name} schema_version must be {expected_schema}")
        ready_field = entry["ready_field"]
        if ready_field:
            entry["ready"] = payload.get(ready_field) is True
            if payload.get(ready_field) is not True:
                blockers.append(f"{name} must have {ready_field}=true")
        if _as_list(payload.get("blockers")):
            blockers.append(f"{name} must have no blockers")
        if payload.get("ready_for_cutover") is not None and payload.get(
            "ready_for_cutover"
        ) is not False:
            blockers.append(f"{name} must have ready_for_cutover=false")
    return entry, payload, blockers


def _artifact_paths(
    *,
    evidence_json: Path,
    evidence_report: dict[str, Any],
    packet_report: dict[str, Any],
    operator_evidence_template_json: str | Path | None,
) -> dict[str, str]:
    paths = {
        "evidence_json": str(evidence_json),
        "rehearsal_json": _as_str(evidence_report.get("rehearsal_json")),
        "implementation_packet_json": _as_str(
            evidence_report.get("implementation_packet_json")
        ),
        "operator_evidence_md": _as_str(evidence_report.get("operator_evidence_md")),
        "next_action_json": _as_str(packet_report.get("next_action_json")),
        "dry_run_json": _as_str(packet_report.get("dry_run_json")),
        "readiness_json": _as_str(packet_report.get("readiness_json")),
        "handoff_json": _as_str(packet_report.get("handoff_json")),
        "plan_json": _as_str(packet_report.get("plan_json")),
        "source_preflight_json": _as_str(packet_report.get("source_preflight_json")),
        "target_preflight_json": _as_str(packet_report.get("target_preflight_json")),
    }
    if operator_evidence_template_json:
        paths["operator_evidence_template_json"] = str(operator_evidence_template_json)
    return paths


def build_rehearsal_evidence_archive_report(
    *,
    evidence_json: str | Path,
    operator_evidence_template_json: str | Path | None = None,
) -> dict[str, Any]:
    """Build a DB-free archive manifest for a completed rehearsal evidence chain."""
    evidence_path = Path(evidence_json)
    evidence_report, evidence_error = _read_json_object(evidence_path)
    blockers: list[str] = []
    if evidence_error:
        evidence_report = {}
        blockers.append(f"evidence report {evidence_error}")
    assert evidence_report is not None

    packet_path = Path(_as_str(evidence_report.get("implementation_packet_json")))
    packet_report, packet_error = _read_json_object(packet_path)
    if packet_error:
        packet_report = {}
        blockers.append(f"implementation packet {packet_error}")
    assert packet_report is not None

    if evidence_report.get("schema_version") != evidence.SCHEMA_VERSION:
        blockers.append(f"evidence report schema_version must be {evidence.SCHEMA_VERSION}")
    if evidence_report.get("ready_for_rehearsal_evidence") is not True:
        blockers.append("evidence report must have ready_for_rehearsal_evidence=true")
    if evidence_report.get("operator_rehearsal_evidence_accepted") is not True:
        blockers.append(
            "evidence report must have operator_rehearsal_evidence_accepted=true"
        )
    if evidence_report.get("ready_for_cutover") is not False:
        blockers.append("evidence report must have ready_for_cutover=false")
    if _as_list(evidence_report.get("blockers")):
        blockers.append("evidence report must have no blockers")

    paths = _artifact_paths(
        evidence_json=evidence_path,
        evidence_report=evidence_report,
        packet_report=packet_report,
        operator_evidence_template_json=operator_evidence_template_json,
    )
    artifacts: list[dict[str, Any]] = []
    loaded_payloads: dict[str, dict[str, Any]] = {}
    for name, path_text in paths.items():
        entry, payload, entry_blockers = _artifact_entry(name=name, path_text=path_text)
        artifacts.append(entry)
        blockers.extend(entry_blockers)
        if payload is not None:
            loaded_payloads[name] = payload

    template_report = loaded_payloads.get("operator_evidence_template_json")
    if template_report is not None:
        template_output_md = _as_str(template_report.get("output_md"))
        operator_evidence_md = paths["operator_evidence_md"]
        if template_output_md and not _same_path(template_output_md, operator_evidence_md):
            blockers.append(
                "operator_evidence_template_json output_md must match operator_evidence_md"
            )

    tenant_id = _as_str(evidence_report.get("tenant_id"))
    target_schema = _as_str(evidence_report.get("target_schema"))
    target_url = _as_str(evidence_report.get("target_url"))
    for name, payload in loaded_payloads.items():
        if name == "operator_evidence_template_json":
            continue
        payload_tenant = _as_str(payload.get("tenant_id"))
        if tenant_id and payload_tenant and payload_tenant != tenant_id:
            blockers.append(f"{name} tenant_id must match evidence report")
        payload_schema = _as_str(payload.get("target_schema"))
        if target_schema and payload_schema and payload_schema != target_schema:
            blockers.append(f"{name} target_schema must match evidence report")

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_json": str(evidence_path),
        "operator_evidence_template_json": (
            str(operator_evidence_template_json)
            if operator_evidence_template_json
            else ""
        ),
        "tenant_id": tenant_id,
        "target_schema": target_schema,
        "target_url": target_url,
        "ready_for_archive": not blockers,
        "ready_for_cutover": False,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Evidence Archive Manifest",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for archive: `{str(report['ready_for_archive']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Artifact count: `{report['artifact_count']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "| Artifact | Ready | Bytes | SHA-256 | Path |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for item in report["artifacts"]:
        lines.append(
            "| "
            f"`{item['artifact']}` | "
            f"`{str(item['ready']).lower()}` | "
            f"{item['bytes']} | "
            f"`{item['sha256']}` | "
            f"`{item['path']}` |"
        )
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This manifest proves that non-production rehearsal evidence artifacts "
            "are present, hashable, and internally consistent. It does not authorize "
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_evidence_archive",
        description="Build a DB-free P3.4.2 rehearsal evidence archive manifest.",
    )
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--operator-evidence-template-json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless all archive artifacts are present and accepted.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_rehearsal_evidence_archive_report(
            evidence_json=args.evidence_json,
            operator_evidence_template_json=args.operator_evidence_template_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_archive"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
