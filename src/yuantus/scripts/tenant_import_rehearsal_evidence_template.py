from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts.tenant_import_rehearsal_evidence import (
    PASS_RESULTS,
    SIGN_OFF_HEADING,
)


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-evidence-template-v1"
PLACEHOLDER = "<fill-before-evidence-gate>"


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


def _redact_url(url: str) -> str:
    if not url or "://" not in url:
        return url
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return url


def _value_or_placeholder(value: str) -> str:
    return value.strip() if value.strip() else PLACEHOLDER


def _is_pass_result(value: str) -> bool:
    return " ".join(value.split()).casefold() in PASS_RESULTS


def build_operator_evidence_template_report(
    *,
    rehearsal_json: str | Path,
    backup_restore_owner: str = "",
    rehearsal_window: str = "",
    rehearsal_executed_by: str = "",
    rehearsal_result: str = "",
    evidence_reviewer: str = "",
    evidence_date: str = "",
    output_md: str | Path = "",
) -> dict[str, Any]:
    """Build operator evidence Markdown from a green rehearsal report."""
    rehearsal_path = Path(rehearsal_json)
    rehearsal_report, read_error = _read_json_object(rehearsal_path)
    blockers: list[str] = []
    if read_error:
        rehearsal_report = {}
        blockers.append(f"rehearsal report {read_error}")
    assert rehearsal_report is not None

    if rehearsal_report.get("schema_version") != tenant_import_rehearsal.SCHEMA_VERSION:
        blockers.append(
            "rehearsal report schema_version must be "
            f"{tenant_import_rehearsal.SCHEMA_VERSION}"
        )
    if rehearsal_report.get("ready_for_rehearsal_import") is not True:
        blockers.append("rehearsal report must have ready_for_rehearsal_import=true")
    if rehearsal_report.get("import_executed") is not True:
        blockers.append("rehearsal report must have import_executed=true")
    if rehearsal_report.get("db_connection_attempted") is not True:
        blockers.append("rehearsal report must have db_connection_attempted=true")
    if rehearsal_report.get("ready_for_cutover") is not False:
        blockers.append("rehearsal report must have ready_for_cutover=false")
    if _as_list(rehearsal_report.get("blockers")):
        blockers.append("rehearsal report must have no blockers")

    tenant_id = _as_str(rehearsal_report.get("tenant_id"))
    target_schema = _as_str(rehearsal_report.get("target_schema"))
    target_url = _redact_url(_as_str(rehearsal_report.get("target_url")))
    if not tenant_id:
        blockers.append("rehearsal report missing tenant_id")
    if not target_schema:
        blockers.append("rehearsal report missing target_schema")
    if not target_url:
        blockers.append("rehearsal report missing target_url")

    sign_off = {
        "Pilot tenant": tenant_id or PLACEHOLDER,
        "Non-production rehearsal DB": target_url or PLACEHOLDER,
        "Backup/restore owner": _value_or_placeholder(backup_restore_owner),
        "Rehearsal window": _value_or_placeholder(rehearsal_window),
        "Rehearsal executed by": _value_or_placeholder(rehearsal_executed_by),
        "Rehearsal result": _value_or_placeholder(rehearsal_result),
        "Evidence reviewer": _value_or_placeholder(evidence_reviewer),
        "Date": _value_or_placeholder(evidence_date),
    }

    for key, value in sign_off.items():
        if value == PLACEHOLDER:
            blockers.append(f"operator evidence template missing {key}")
    if sign_off["Rehearsal result"] != PLACEHOLDER and not _is_pass_result(
        sign_off["Rehearsal result"]
    ):
        blockers.append("operator evidence template Rehearsal result must be pass")

    return {
        "schema_version": SCHEMA_VERSION,
        "rehearsal_json": str(rehearsal_path),
        "output_md": str(output_md) if output_md else "",
        "tenant_id": tenant_id,
        "target_schema": target_schema,
        "target_url": target_url,
        "ready_for_operator_evidence_template": not blockers,
        "ready_for_cutover": False,
        "operator_sign_off": sign_off,
        "blockers": blockers,
    }


def render_operator_evidence_markdown(report: dict[str, Any]) -> str:
    sign_off = report["operator_sign_off"]
    return "\n".join(
        [
            "# Tenant Import Rehearsal Operator Evidence",
            "",
            f"- Template schema: `{report['schema_version']}`",
            f"- Rehearsal JSON: `{report['rehearsal_json']}`",
            f"- Target schema: `{report['target_schema']}`",
            f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
            "",
            SIGN_OFF_HEADING,
            "",
            "```text",
            f"Pilot tenant: {sign_off['Pilot tenant']}",
            f"Non-production rehearsal DB: {sign_off['Non-production rehearsal DB']}",
            f"Backup/restore owner: {sign_off['Backup/restore owner']}",
            f"Rehearsal window: {sign_off['Rehearsal window']}",
            f"Rehearsal executed by: {sign_off['Rehearsal executed by']}",
            f"Rehearsal result: {sign_off['Rehearsal result']}",
            f"Evidence reviewer: {sign_off['Evidence reviewer']}",
            f"Date: {sign_off['Date']}",
            "```",
            "",
            "## Scope",
            "",
            "This file is operator evidence for a non-production rehearsal only. "
            "It does not authorize production cutover.",
            "",
        ]
    )


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_operator_evidence_markdown(report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal_evidence_template",
        description="Render P3.4.2 operator evidence Markdown from a green rehearsal report.",
    )
    parser.add_argument("--rehearsal-json", required=True)
    parser.add_argument("--backup-restore-owner", default="")
    parser.add_argument("--rehearsal-window", default="")
    parser.add_argument("--rehearsal-executed-by", default="")
    parser.add_argument("--rehearsal-result", default="")
    parser.add_argument("--evidence-reviewer", default="")
    parser.add_argument("--date", default="")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the generated operator evidence is ready for the evidence gate.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_operator_evidence_template_report(
            rehearsal_json=args.rehearsal_json,
            backup_restore_owner=args.backup_restore_owner,
            rehearsal_window=args.rehearsal_window,
            rehearsal_executed_by=args.rehearsal_executed_by,
            rehearsal_result=args.rehearsal_result,
            evidence_reviewer=args.evidence_reviewer,
            evidence_date=args.date,
            output_md=args.output_md,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_operator_evidence_template"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
