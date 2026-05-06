from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from yuantus.scripts import tenant_import_rehearsal
from yuantus.scripts import tenant_import_rehearsal_implementation_packet as packet
from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser
from yuantus.scripts.tenant_schema import GLOBAL_TABLE_NAMES


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-evidence-v1"
SIGN_OFF_HEADING = "## Rehearsal Evidence Sign-Off"
SIGN_OFF_FIELDS = (
    "Pilot tenant",
    "Non-production rehearsal DB",
    "Backup/restore owner",
    "Rehearsal window",
    "Rehearsal executed by",
    "Rehearsal result",
    "Evidence reviewer",
    "Date",
)
PASS_RESULTS = frozenset({"pass", "passed", "green", "success", "successful"})
PLACEHOLDER_VALUES = frozenset({"tbd", "todo", "pending", "n/a", "na", "none", "-"})
_REQUIRED_PACKET_FIELDS = (
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


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _looks_like_placeholder(value: str) -> bool:
    normalized = _normalize_text(value)
    return (
        not normalized
        or normalized in PLACEHOLDER_VALUES
        or (normalized.startswith("<") and normalized.endswith(">"))
        or normalized == "..."
    )


def _redact_url(url: str) -> str:
    if not url or "://" not in url:
        return url
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return url


def _url_identity(url: str) -> tuple[str, str | None, str | None, int | None, str | None]:
    parsed = make_url(url)
    driver_family = (
        "postgres" if parsed.drivername.startswith("postgres") else parsed.drivername
    )
    return (
        driver_family,
        parsed.username,
        parsed.host,
        parsed.port,
        parsed.database,
    )


def _same_database(left: str, right: str) -> bool:
    try:
        return _url_identity(left) == _url_identity(right)
    except Exception:
        return _normalize_text(left) == _normalize_text(right)


def _same_path(left: str, right: Path) -> bool:
    left_path = Path(left)
    try:
        if left_path.exists() and right.exists():
            return left_path.resolve() == right.resolve()
    except OSError:
        pass
    return str(left_path) == str(right)


def _find_sign_off_section(text: str) -> str:
    start = text.find(SIGN_OFF_HEADING)
    if start == -1:
        return ""
    start = text.find("\n", start) + 1
    end = text.find("\n## ", start)
    if end == -1:
        end = len(text)
    return text[start:end]


def parse_operator_sign_off(path: Path) -> dict[str, str]:
    section = _find_sign_off_section(path.read_text(encoding="utf-8"))
    match = re.search(r"```(?:text)?\n(?P<body>.*?)\n```", section, flags=re.DOTALL)
    body = match.group("body") if match else section

    values: dict[str, str] = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in SIGN_OFF_FIELDS:
            values[key] = value.strip()
    return values


def _sign_off_summary(values: dict[str, str]) -> dict[str, str]:
    return {
        field: (
            _redact_url(values.get(field, ""))
            if field == "Non-production rehearsal DB"
            else values.get(field, "")
        )
        for field in SIGN_OFF_FIELDS
    }


def _validate_operator_sign_off(
    *,
    values: dict[str, str],
    tenant_id: str,
    target_url: str,
) -> list[str]:
    blockers: list[str] = []
    for field in SIGN_OFF_FIELDS:
        if _looks_like_placeholder(values.get(field, "")):
            blockers.append(f"operator evidence missing {field}")

    pilot_tenant = values.get("Pilot tenant", "")
    if pilot_tenant and _normalize_text(pilot_tenant) != _normalize_text(tenant_id):
        blockers.append("operator evidence Pilot tenant must match rehearsal report")

    rehearsal_db = values.get("Non-production rehearsal DB", "")
    if rehearsal_db and not _looks_like_placeholder(rehearsal_db):
        if "://" not in rehearsal_db:
            blockers.append("operator evidence Non-production rehearsal DB must be a URL")
        elif not _same_database(rehearsal_db, target_url):
            blockers.append(
                "operator evidence Non-production rehearsal DB must match rehearsal target_url"
            )

    result = values.get("Rehearsal result", "")
    if result and _normalize_text(result) not in PASS_RESULTS:
        blockers.append("operator evidence Rehearsal result must be pass")
    return blockers


def _validate_packet(
    *,
    packet_report: dict[str, Any],
    rehearsal_report: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if packet_report.get("schema_version") != packet.SCHEMA_VERSION:
        blockers.append(f"implementation packet schema_version must be {packet.SCHEMA_VERSION}")
    if packet_report.get("ready_for_claude_importer") is not True:
        blockers.append("implementation packet must have ready_for_claude_importer=true")
    if packet_report.get("ready_for_cutover") is not False:
        blockers.append("implementation packet must have ready_for_cutover=false")
    if _as_list(packet_report.get("blockers")):
        blockers.append("implementation packet must have no blockers")
    for key in ("tenant_id", "target_schema", "target_url"):
        if _as_str(packet_report.get(key)) != _as_str(rehearsal_report.get(key)):
            blockers.append(f"implementation packet {key} must match rehearsal report")

    next_action_json = _as_str(packet_report.get("next_action_json"))
    if not next_action_json:
        blockers.append("implementation packet missing next_action_json")
        return blockers

    try:
        fresh_report = packet.build_implementation_packet_report(
            next_action_json,
            output_md=_as_str(packet_report.get("implementation_md"))
            or "tenant_import_rehearsal_evidence.md",
        )
    except Exception as exc:
        blockers.append(f"fresh implementation packet validation failed: {exc}")
        return blockers

    for blocker in _as_list(fresh_report.get("blockers")):
        blockers.append(f"fresh {blocker}")
    if fresh_report.get("ready_for_claude_importer") is not True:
        blockers.append(
            "fresh implementation packet validation must have "
            "ready_for_claude_importer=true"
        )
    for key in _REQUIRED_PACKET_FIELDS:
        if _as_str(packet_report.get(key)) != _as_str(fresh_report.get(key)):
            blockers.append(f"implementation packet {key} must match fresh validation")
    return blockers


def _validate_rehearsal_report(
    *,
    rehearsal_report: dict[str, Any],
    rehearsal_json: Path,
    implementation_packet_json: Path,
) -> list[str]:
    blockers: list[str] = []
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
    report_packet = _as_str(rehearsal_report.get("implementation_packet_json"))
    if report_packet and not _same_path(report_packet, implementation_packet_json):
        blockers.append("rehearsal report implementation_packet_json must match input")

    table_results = rehearsal_report.get("table_results")
    if not isinstance(table_results, list) or not table_results:
        blockers.append("rehearsal report table_results must be non-empty")
        return blockers

    seen: set[str] = set()
    for index, row in enumerate(table_results):
        if not isinstance(row, dict):
            blockers.append(f"table_results[{index}] must be an object")
            continue
        table = _as_str(row.get("table"))
        if not table:
            blockers.append(f"table_results[{index}] missing table")
            continue
        if table in seen:
            blockers.append(f"table_results contains duplicate table {table}")
        seen.add(table)
        if table in GLOBAL_TABLE_NAMES:
            blockers.append(f"table_results includes global/control-plane table {table}")
        if row.get("row_count_matches") is not True:
            blockers.append(f"{table} row_count_matches must be true")
        expected = row.get("source_rows_expected")
        inserted = row.get("target_rows_inserted")
        if not isinstance(expected, int) or not isinstance(inserted, int):
            blockers.append(f"{table} row counts must be integers")
        elif expected != inserted:
            blockers.append(f"{table} inserted {inserted} rows; expected {expected}")
    return blockers


def build_rehearsal_evidence_report(
    *,
    rehearsal_json: str | Path,
    implementation_packet_json: str | Path,
    operator_evidence_md: str | Path,
) -> dict[str, Any]:
    """Validate operator rehearsal evidence without opening database connections."""
    rehearsal_path = Path(rehearsal_json)
    packet_path = Path(implementation_packet_json)
    evidence_path = Path(operator_evidence_md)
    blockers: list[str] = []

    rehearsal_report, rehearsal_error = _read_json_object(rehearsal_path)
    packet_report, packet_error = _read_json_object(packet_path)
    if rehearsal_error:
        blockers.append(f"rehearsal report {rehearsal_error}")
    if packet_error:
        blockers.append(f"implementation packet {packet_error}")

    operator_sign_off: dict[str, str] = {}
    if not evidence_path.is_file():
        blockers.append(f"operator evidence {evidence_path} does not exist")
    else:
        operator_sign_off = parse_operator_sign_off(evidence_path)

    if rehearsal_report is None:
        rehearsal_report = {}
    if packet_report is None:
        packet_report = {}

    blockers.extend(
        _validate_rehearsal_report(
            rehearsal_report=rehearsal_report,
            rehearsal_json=rehearsal_path,
            implementation_packet_json=packet_path,
        )
    )
    blockers.extend(
        _validate_packet(
            packet_report=packet_report,
            rehearsal_report=rehearsal_report,
        )
    )
    if evidence_path.is_file():
        blockers.extend(
            _validate_operator_sign_off(
                values=operator_sign_off,
                tenant_id=_as_str(rehearsal_report.get("tenant_id")),
                target_url=_as_str(rehearsal_report.get("target_url")),
            )
        )

    table_results = rehearsal_report.get("table_results")
    if not isinstance(table_results, list):
        table_results = []
    ready = not blockers
    return {
        "schema_version": SCHEMA_VERSION,
        "rehearsal_json": str(rehearsal_path),
        "implementation_packet_json": str(packet_path),
        "operator_evidence_md": str(evidence_path),
        "tenant_id": _as_str(rehearsal_report.get("tenant_id")),
        "target_schema": _as_str(rehearsal_report.get("target_schema")),
        "target_url": _redact_url(_as_str(rehearsal_report.get("target_url"))),
        "rehearsal_schema_version": rehearsal_report.get("schema_version", ""),
        "implementation_packet_schema_version": packet_report.get("schema_version", ""),
        "ready_for_rehearsal_evidence": ready,
        "operator_rehearsal_evidence_accepted": ready,
        "ready_for_cutover": False,
        "table_results": table_results,
        "operator_sign_off": _sign_off_summary(operator_sign_off),
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Evidence Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Rehearsal evidence accepted: `{str(report['ready_for_rehearsal_evidence']).lower()}`",
        f"- Operator evidence accepted: `{str(report['operator_rehearsal_evidence_accepted']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Rehearsal JSON: `{report['rehearsal_json']}`",
        f"- Implementation packet JSON: `{report['implementation_packet_json']}`",
        f"- Operator evidence MD: `{report['operator_evidence_md']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Operator Sign-Off",
            "",
            "| Field | Value |",
            "| --- | --- |",
        ]
    )
    for field, value in report["operator_sign_off"].items():
        lines.append(f"| `{field}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Table Results",
            "",
            "| Table | Source rows expected | Target rows inserted | Matches |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for result in report.get("table_results") or []:
        if not isinstance(result, dict):
            continue
        lines.append(
            "| "
            f"`{result.get('table', '')}` | "
            f"{result.get('source_rows_expected', '')} | "
            f"{result.get('target_rows_inserted', '')} | "
            f"`{str(result.get('row_count_matches')).lower()}` |"
        )
    if not report.get("table_results"):
        lines.append("| None | 0 | 0 | `false` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This report accepts or rejects non-production rehearsal evidence only. "
            "It does not authorize production cutover, does not change runtime "
            "tenancy mode, and does not open database connections.",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_evidence",
        description="Validate P3.4.2 operator rehearsal evidence without DB access.",
    )
    parser.add_argument("--rehearsal-json", required=True)
    parser.add_argument("--implementation-packet-json", required=True)
    parser.add_argument("--operator-evidence-md", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless operator rehearsal evidence is accepted.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_rehearsal_evidence_report(
            rehearsal_json=args.rehearsal_json,
            implementation_packet_json=args.implementation_packet_json,
            operator_evidence_md=args.operator_evidence_md,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_rehearsal_evidence"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
