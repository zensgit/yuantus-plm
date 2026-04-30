from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_evidence_handoff as handoff
from yuantus.scripts import tenant_import_rehearsal_evidence_intake as intake


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-reviewer-packet-v1"


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


def _artifact_summaries(report: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in report.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        summaries.append(
            {
                "artifact": _as_str(item.get("artifact")),
                "path": _as_str(item.get("path")),
                "ready": item.get("ready") is True,
                "synthetic_drill": item.get("synthetic_drill") is True,
            }
        )
    return summaries


def _archive_summaries(report: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in report.get("archive_artifacts") or []:
        if not isinstance(item, dict):
            continue
        summaries.append(
            {
                "artifact": _as_str(item.get("artifact")),
                "path": _as_str(item.get("path")),
                "ready": item.get("ready") is True,
                "sha256": _as_str(item.get("sha256")),
            }
        )
    return summaries


def build_reviewer_packet_report(
    *,
    evidence_intake_json: str | Path,
    evidence_handoff_json: str | Path,
) -> dict[str, Any]:
    """Build a reviewer handoff packet from green intake and handoff reports."""
    intake_path = Path(evidence_intake_json)
    handoff_path = Path(evidence_handoff_json)
    intake_report, intake_error = _read_json_object(intake_path)
    handoff_report, handoff_error = _read_json_object(handoff_path)
    blockers: list[str] = []
    if intake_error:
        intake_report = {}
        blockers.append(f"evidence intake {intake_error}")
    if handoff_error:
        handoff_report = {}
        blockers.append(f"evidence handoff {handoff_error}")
    assert intake_report is not None
    assert handoff_report is not None

    if intake_report.get("schema_version") != intake.SCHEMA_VERSION:
        blockers.append(f"evidence intake schema_version must be {intake.SCHEMA_VERSION}")
    if intake_report.get("ready_for_evidence_intake") is not True:
        blockers.append("evidence intake must have ready_for_evidence_intake=true")
    if intake_report.get("redaction_ready") is not True:
        blockers.append("evidence intake must have redaction_ready=true")
    if intake_report.get("ready_for_cutover") is not False:
        blockers.append("evidence intake must have ready_for_cutover=false")
    if _as_list(intake_report.get("blockers")):
        blockers.append("evidence intake must have no blockers")

    if handoff_report.get("schema_version") != handoff.SCHEMA_VERSION:
        blockers.append(
            f"evidence handoff schema_version must be {handoff.SCHEMA_VERSION}"
        )
    if handoff_report.get("ready_for_evidence_handoff") is not True:
        blockers.append("evidence handoff must have ready_for_evidence_handoff=true")
    if handoff_report.get("ready_for_cutover") is not False:
        blockers.append("evidence handoff must have ready_for_cutover=false")
    if _as_list(handoff_report.get("blockers")):
        blockers.append("evidence handoff must have no blockers")

    for key in ("tenant_id", "target_schema", "target_url"):
        if _as_str(intake_report.get(key)) != _as_str(handoff_report.get(key)):
            blockers.append(f"{key} must match between intake and handoff reports")

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_intake_json": str(intake_path),
        "evidence_intake_schema_version": intake_report.get("schema_version", ""),
        "evidence_handoff_json": str(handoff_path),
        "evidence_handoff_schema_version": handoff_report.get("schema_version", ""),
        "tenant_id": _as_str(intake_report.get("tenant_id")),
        "target_schema": _as_str(intake_report.get("target_schema")),
        "target_url": _as_str(intake_report.get("target_url")),
        "intake_artifact_count": intake_report.get("artifact_count", 0),
        "handoff_archive_artifact_count": handoff_report.get(
            "archive_artifact_count",
            0,
        ),
        "redaction_artifact_count": intake_report.get("redaction_artifact_count", 0),
        "intake_artifacts": _artifact_summaries(intake_report),
        "archive_artifacts": _archive_summaries(handoff_report),
        "ready_for_reviewer_packet": not blockers,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Reviewer Packet",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for reviewer packet: `{str(report['ready_for_reviewer_packet']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Evidence intake JSON: `{report['evidence_intake_json']}`",
        f"- Evidence handoff JSON: `{report['evidence_handoff_json']}`",
        f"- Intake artifact count: `{report['intake_artifact_count']}`",
        f"- Handoff archive artifact count: `{report['handoff_archive_artifact_count']}`",
        f"- Redaction artifact count: `{report['redaction_artifact_count']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Intake Artifacts",
            "",
            "| Artifact | Ready | Synthetic | Path |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in report["intake_artifacts"]:
        lines.append(
            "| "
            f"`{item['artifact']}` | "
            f"`{str(item['ready']).lower()}` | "
            f"`{str(item['synthetic_drill']).lower()}` | "
            f"`{item['path']}` |"
        )
    if not report["intake_artifacts"]:
        lines.append("| None | `false` | `false` | `` |")
    lines.extend(
        [
            "",
            "## Archive Artifacts",
            "",
            "| Artifact | Ready | SHA-256 | Path |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in report["archive_artifacts"]:
        lines.append(
            "| "
            f"`{item['artifact']}` | "
            f"`{str(item['ready']).lower()}` | "
            f"`{item['sha256']}` | "
            f"`{item['path']}` |"
        )
    if not report["archive_artifacts"]:
        lines.append("| None | `false` | `` | `` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This reviewer packet reads completed intake and handoff reports only. "
            "It does not open database connections, run rehearsal commands, "
            "accept evidence, build an archive, run cutover, or enable runtime "
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
    parser = argparse.ArgumentParser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal_reviewer_packet",
        description="Build a DB-free P3.4.2 reviewer handoff packet.",
    )
    parser.add_argument("--evidence-intake-json", required=True)
    parser.add_argument("--evidence-handoff-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the reviewer packet is ready.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_reviewer_packet_report(
            evidence_intake_json=args.evidence_intake_json,
            evidence_handoff_json=args.evidence_handoff_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_reviewer_packet"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
