from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from yuantus.scripts.tenant_migration_dry_run import (
    BASELINE_REVISION,
    SCHEMA_VERSION as DRY_RUN_SCHEMA_VERSION,
)


SCHEMA_VERSION = "p3.4.2-import-rehearsal-readiness-v1"
SIGN_OFF_HEADING = "## 6. Sign-Off"
SIGN_OFF_FIELDS = (
    "Pilot tenant",
    "PostgreSQL rehearsal DSN",
    "Backup/restore owner",
    "Rehearsal window",
    "Reviewer",
    "Decision",
    "Date",
)
APPROVED_DECISIONS = frozenset({"approved", "approve", "signed off", "sign off"})
PLACEHOLDER_VALUES = frozenset({"tbd", "todo", "pending", "n/a", "na", "none", "-"})


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _as_non_empty_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _redact_url(url: str) -> str:
    return make_url(url).render_as_string(hide_password=True)


def _url_identity(
    url: str,
) -> tuple[str, str | None, str | None, int | None, str | None]:
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


def _is_postgres_url(url: str) -> bool:
    try:
        drivername = make_url(url).drivername
    except Exception:
        return False
    return drivername.startswith("postgresql") or drivername.startswith("postgres")


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


def _find_sign_off_section(text: str) -> str:
    start = text.find(SIGN_OFF_HEADING)
    if start == -1:
        return ""
    start = text.find("\n", start) + 1
    end = text.find("\n## ", start)
    if end == -1:
        end = len(text)
    return text[start:end]


def parse_classification_sign_off(path: Path) -> dict[str, str]:
    """Extract the tracked stop-gate sign-off block without exposing secrets."""
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


def _redact_sign_off_dsn(value: str) -> str:
    if not value or "://" not in value:
        return value
    try:
        return _redact_url(value)
    except Exception:
        return value


def _classification_sign_off_summary(values: dict[str, str]) -> dict[str, str]:
    return {
        field: (
            _redact_sign_off_dsn(values.get(field, ""))
            if field == "PostgreSQL rehearsal DSN"
            else values.get(field, "")
        )
        for field in SIGN_OFF_FIELDS
    }


def _validate_classification_sign_off(
    *,
    values: dict[str, str],
    tenant_id: str,
    target_url: str,
    backup_restore_owner: str,
    rehearsal_window: str,
) -> list[str]:
    blockers: list[str] = []
    for field in SIGN_OFF_FIELDS:
        if _looks_like_placeholder(values.get(field, "")):
            blockers.append(f"classification sign-off missing {field}")

    pilot_tenant = values.get("Pilot tenant", "")
    if pilot_tenant and _normalize_text(pilot_tenant) != _normalize_text(tenant_id):
        blockers.append("classification sign-off Pilot tenant must match tenant_id")

    owner = values.get("Backup/restore owner", "")
    if owner and _normalize_text(owner) != _normalize_text(backup_restore_owner):
        blockers.append(
            "classification sign-off Backup/restore owner must match input"
        )

    window = values.get("Rehearsal window", "")
    if window and _normalize_text(window) != _normalize_text(rehearsal_window):
        blockers.append("classification sign-off Rehearsal window must match input")

    decision = values.get("Decision", "")
    if decision and _normalize_text(decision) not in APPROVED_DECISIONS:
        blockers.append("classification sign-off Decision must be approved")

    signed_dsn = values.get("PostgreSQL rehearsal DSN", "")
    if signed_dsn and not _looks_like_placeholder(signed_dsn):
        if "://" not in signed_dsn:
            blockers.append(
                "classification sign-off PostgreSQL rehearsal DSN must be a URL"
            )
        elif not _is_postgres_url(signed_dsn):
            blockers.append(
                "classification sign-off PostgreSQL rehearsal DSN must be PostgreSQL"
            )
        elif target_url and _url_identity(signed_dsn) != _url_identity(target_url):
            blockers.append(
                "classification sign-off PostgreSQL rehearsal DSN must match target_url"
            )

    return blockers


def build_readiness_report(
    *,
    dry_run_json: str | Path,
    tenant_id: str,
    target_url: str,
    target_schema: str,
    backup_restore_owner: str,
    rehearsal_window: str,
    classification_artifact: str | Path,
    classification_signed_off: bool,
) -> dict[str, Any]:
    """Validate P3.4.2 stop-gate inputs without DB connections."""
    dry_run_path = Path(dry_run_json)
    artifact_path = Path(classification_artifact)
    dry_run = _read_json(dry_run_path)

    tenant_id = _as_non_empty_str(tenant_id)
    target_schema = _as_non_empty_str(target_schema)
    target_url = _as_non_empty_str(target_url)
    backup_restore_owner = _as_non_empty_str(backup_restore_owner)
    rehearsal_window = _as_non_empty_str(rehearsal_window)

    blockers: list[str] = []
    if dry_run.get("schema_version") != DRY_RUN_SCHEMA_VERSION:
        blockers.append(f"dry-run schema_version must be {DRY_RUN_SCHEMA_VERSION}")
    if not tenant_id:
        blockers.append("missing tenant id")
    if not target_schema:
        blockers.append("missing target schema")
    if not target_url:
        blockers.append("missing non-production PostgreSQL target URL")
    elif not _is_postgres_url(target_url):
        blockers.append("target_url must be a PostgreSQL URL")
    if not backup_restore_owner:
        blockers.append("missing backup/restore owner")
    if not rehearsal_window:
        blockers.append("missing rehearsal window")
    if not artifact_path.is_file():
        blockers.append("classification artifact is missing")
    if not classification_signed_off:
        blockers.append("classification artifact must be signed off")
    sign_off_values: dict[str, str] = {}
    if artifact_path.is_file():
        sign_off_values = parse_classification_sign_off(artifact_path)
        if classification_signed_off:
            blockers.extend(
                _validate_classification_sign_off(
                    values=sign_off_values,
                    tenant_id=tenant_id,
                    target_url=target_url,
                    backup_restore_owner=backup_restore_owner,
                    rehearsal_window=rehearsal_window,
                )
            )

    if dry_run.get("ready_for_import") is not True:
        blockers.append("dry-run report must have ready_for_import=true")
    if dry_run.get("blockers"):
        blockers.append("dry-run report must have no blockers")
    if dry_run.get("baseline_revision") != BASELINE_REVISION:
        blockers.append(f"dry-run baseline_revision must be {BASELINE_REVISION}")
    if tenant_id and dry_run.get("tenant_id") != tenant_id:
        blockers.append("tenant_id must match dry-run tenant_id")
    if target_schema and dry_run.get("target_schema") != target_schema:
        blockers.append("target_schema must match dry-run target_schema")

    redacted_target_url = _redact_url(target_url) if target_url else ""
    return {
        "schema_version": SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "target_schema": target_schema,
        "target_url": redacted_target_url,
        "dry_run_schema_version": dry_run.get("schema_version"),
        "ready_for_import": dry_run.get("ready_for_import") is True,
        "ready_for_rehearsal": not blockers,
        "checks": {
            "backup_restore_owner": backup_restore_owner,
            "rehearsal_window": rehearsal_window,
            "classification_artifact": str(artifact_path),
            "classification_signed_off": classification_signed_off,
            "classification_sign_off": _classification_sign_off_summary(
                sign_off_values
            ),
            "dry_run_json": str(dry_run_path),
            "dry_run_blocker_count": len(dry_run.get("blockers") or []),
            "baseline_revision": dry_run.get("baseline_revision"),
        },
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    checks = report["checks"]
    lines = [
        "# Tenant Import Rehearsal Readiness Report",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for rehearsal: `{str(report['ready_for_rehearsal']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Dry-run schema version: `{report['dry_run_schema_version']}`",
        f"- Dry-run ready for import: `{str(report['ready_for_import']).lower()}`",
        f"- Backup/restore owner: `{checks['backup_restore_owner']}`",
        f"- Rehearsal window: `{checks['rehearsal_window']}`",
        f"- Classification artifact: `{checks['classification_artifact']}`",
        f"- Classification signed off: `{str(checks['classification_signed_off']).lower()}`",
        "",
        "## Classification Sign-Off",
        "",
    ]
    for field, value in checks["classification_sign_off"].items():
        lines.append(f"- {field}: `{value}`")
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m yuantus.scripts.tenant_import_rehearsal_readiness",
        description="Validate P3.4.2 tenant import rehearsal readiness inputs.",
    )
    parser.add_argument("--dry-run-json", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--target-schema", required=True)
    parser.add_argument("--backup-restore-owner", required=True)
    parser.add_argument("--rehearsal-window", required=True)
    parser.add_argument("--classification-artifact", required=True)
    parser.add_argument("--classification-signed-off", action="store_true")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when readiness blockers are present.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_readiness_report(
            dry_run_json=args.dry_run_json,
            tenant_id=args.tenant_id,
            target_url=args.target_url,
            target_schema=args.target_schema,
            backup_restore_owner=args.backup_restore_owner,
            rehearsal_window=args.rehearsal_window,
            classification_artifact=args.classification_artifact,
            classification_signed_off=args.classification_signed_off,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and report["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
