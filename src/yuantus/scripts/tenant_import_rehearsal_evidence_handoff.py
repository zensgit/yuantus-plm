from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_evidence_archive as archive
from yuantus.scripts import tenant_import_rehearsal_redaction_guard as redaction_guard


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-evidence-handoff-v1"


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


def _same_path(left: str, right: str) -> bool:
    left_path = Path(left)
    right_path = Path(right)
    try:
        if left_path.exists() and right_path.exists():
            return left_path.resolve() == right_path.resolve()
    except OSError:
        pass
    return str(left_path) == str(right_path)


def _archive_artifact_paths(report: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for item in report.get("artifacts") or []:
        if isinstance(item, dict):
            path = _as_str(item.get("path"))
            if path:
                paths.append(path)
    return paths


def _redaction_artifact_paths(report: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for item in report.get("artifacts") or []:
        if isinstance(item, dict):
            path = _as_str(item.get("path"))
            if path:
                paths.append(path)
    return paths


def _artifact_statuses(report: dict[str, Any]) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for item in report.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        statuses.append(
            {
                "artifact": _as_str(item.get("artifact")),
                "path": _as_str(item.get("path")),
                "ready": item.get("ready") is True,
                "sha256": _as_str(item.get("sha256")),
            }
        )
    return statuses


def _missing_redaction_coverage(
    archive_paths: list[str],
    redaction_paths: list[str],
) -> list[str]:
    missing: list[str] = []
    for archive_path in archive_paths:
        if not any(_same_path(archive_path, redaction_path) for redaction_path in redaction_paths):
            missing.append(archive_path)
    return missing


def build_evidence_handoff_report(
    *,
    archive_json: str | Path,
    redaction_guard_json: str | Path,
) -> dict[str, Any]:
    """Validate archive + redaction coverage before evidence handoff."""
    archive_path = Path(archive_json)
    redaction_path = Path(redaction_guard_json)
    archive_report, archive_error = _read_json_object(archive_path)
    redaction_report, redaction_error = _read_json_object(redaction_path)
    blockers: list[str] = []
    if archive_error:
        archive_report = {}
        blockers.append(f"archive manifest {archive_error}")
    if redaction_error:
        redaction_report = {}
        blockers.append(f"redaction guard {redaction_error}")
    assert archive_report is not None
    assert redaction_report is not None

    if archive_report.get("schema_version") != archive.SCHEMA_VERSION:
        blockers.append(f"archive manifest schema_version must be {archive.SCHEMA_VERSION}")
    if archive_report.get("ready_for_archive") is not True:
        blockers.append("archive manifest must have ready_for_archive=true")
    if archive_report.get("ready_for_cutover") is not False:
        blockers.append("archive manifest must have ready_for_cutover=false")
    if _as_list(archive_report.get("blockers")):
        blockers.append("archive manifest must have no blockers")

    if redaction_report.get("schema_version") != redaction_guard.SCHEMA_VERSION:
        blockers.append(
            f"redaction guard schema_version must be {redaction_guard.SCHEMA_VERSION}"
        )
    if redaction_report.get("ready_for_artifact_handoff") is not True:
        blockers.append("redaction guard must have ready_for_artifact_handoff=true")
    if redaction_report.get("ready_for_cutover") is not False:
        blockers.append("redaction guard must have ready_for_cutover=false")
    if _as_list(redaction_report.get("blockers")):
        blockers.append("redaction guard must have no blockers")

    archive_paths = _archive_artifact_paths(archive_report)
    redaction_paths = _redaction_artifact_paths(redaction_report)
    if not archive_paths:
        blockers.append("archive manifest must contain artifacts")
    if not redaction_paths:
        blockers.append("redaction guard must contain scanned artifacts")
    for missing_path in _missing_redaction_coverage(archive_paths, redaction_paths):
        blockers.append(f"redaction guard missing archive artifact {missing_path}")

    return {
        "schema_version": SCHEMA_VERSION,
        "archive_json": str(archive_path),
        "archive_schema_version": archive_report.get("schema_version", ""),
        "redaction_guard_json": str(redaction_path),
        "redaction_guard_schema_version": redaction_report.get("schema_version", ""),
        "tenant_id": _as_str(archive_report.get("tenant_id")),
        "target_schema": _as_str(archive_report.get("target_schema")),
        "target_url": _as_str(archive_report.get("target_url")),
        "archive_artifact_count": len(archive_paths),
        "redaction_artifact_count": len(redaction_paths),
        "archive_artifacts": _artifact_statuses(archive_report),
        "ready_for_evidence_handoff": not blockers,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Evidence Handoff",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for evidence handoff: `{str(report['ready_for_evidence_handoff']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Archive JSON: `{report['archive_json']}`",
        f"- Redaction guard JSON: `{report['redaction_guard_json']}`",
        f"- Archive artifact count: `{report['archive_artifact_count']}`",
        f"- Redaction artifact count: `{report['redaction_artifact_count']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
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
            "This handoff gate reads archive and redaction reports only. It does "
            "not open database connections, run rehearsal commands, accept new "
            "evidence, build an archive, authorize production cutover, or enable "
            "runtime schema-per-tenant mode.",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_evidence_handoff",
        description="Validate archive and redaction coverage before P3.4.2 evidence handoff.",
    )
    parser.add_argument("--archive-json", required=True)
    parser.add_argument("--redaction-guard-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless archive and redaction guard are ready for handoff.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_evidence_handoff_report(
            archive_json=args.archive_json,
            redaction_guard_json=args.redaction_guard_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_evidence_handoff"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
