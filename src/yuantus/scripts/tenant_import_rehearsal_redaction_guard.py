from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from yuantus.scripts.tenant_import_cli_safety import build_redacting_parser

SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-redaction-guard-v1"
_POSTGRES_URL_RE = re.compile(
    r"postgres(?:ql)?(?:\+[A-Za-z0-9_]+)?://[^\s`\"'<>]+",
    flags=re.IGNORECASE,
)
_SAFE_PASSWORD_VALUES = frozenset(
    {
        "***",
        "redacted",
        "<redacted>",
        "<password>",
        "<secret>",
        "xxxxx",
        "xxxx",
    }
)


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _candidate_urls(line: str) -> list[str]:
    values: list[str] = []
    for match in _POSTGRES_URL_RE.finditer(line):
        values.append(match.group(0).rstrip(".,;)]}"))
    return values


def _redact_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        return "<unparseable-postgres-url>"


def _plaintext_password_present(url: str) -> bool:
    try:
        parsed = make_url(url)
    except Exception:
        return False
    if not parsed.drivername.lower().startswith("postgres"):
        return False
    password = parsed.password
    if password is None:
        return False
    return password.strip().casefold() not in _SAFE_PASSWORD_VALUES


def _scan_artifact(path: Path) -> tuple[dict[str, Any], list[str]]:
    status: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "readable": False,
        "postgres_url_count": 0,
        "plaintext_password_count": 0,
        "ready": False,
    }
    blockers: list[str] = []
    if not path.is_file():
        blockers.append(f"{path} does not exist")
        return status, blockers

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        blockers.append(f"{path} cannot be read: {exc}")
        return status, blockers

    status["readable"] = True
    plaintext_count = 0
    postgres_count = 0
    for line_no, line in enumerate(text.splitlines(), 1):
        for url in _candidate_urls(line):
            postgres_count += 1
            if _plaintext_password_present(url):
                plaintext_count += 1
                blockers.append(
                    f"{path}:{line_no} contains unredacted PostgreSQL password "
                    f"in {_redact_url(url)}"
                )

    status["postgres_url_count"] = postgres_count
    status["plaintext_password_count"] = plaintext_count
    status["ready"] = not blockers
    return status, blockers


def build_redaction_guard_report(*, artifacts: list[str | Path]) -> dict[str, Any]:
    """Scan P3.4 artifacts for plaintext PostgreSQL passwords without DB access."""
    blockers: list[str] = []
    if not artifacts:
        blockers.append("at least one artifact path is required")

    artifact_statuses: list[dict[str, Any]] = []
    for value in artifacts:
        status, artifact_blockers = _scan_artifact(Path(value))
        artifact_statuses.append(status)
        blockers.extend(artifact_blockers)

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_count": len(artifact_statuses),
        "artifacts": artifact_statuses,
        "ready_for_artifact_handoff": not blockers,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Redaction Guard",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for artifact handoff: `{str(report['ready_for_artifact_handoff']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Artifact count: `{report['artifact_count']}`",
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
            "| Artifact | Exists | Readable | PostgreSQL URLs | Plaintext passwords | Ready |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in report["artifacts"]:
        lines.append(
            "| "
            f"`{item['path']}` | "
            f"`{str(item['exists']).lower()}` | "
            f"`{str(item['readable']).lower()}` | "
            f"{item['postgres_url_count']} | "
            f"{item['plaintext_password_count']} | "
            f"`{str(item['ready']).lower()}` |"
        )
    if not report["artifacts"]:
        lines.append("| None | `false` | `false` | 0 | 0 | `false` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This guard reads local artifacts only. It does not open database "
            "connections, run rehearsal commands, accept evidence, build an "
            "archive, authorize production cutover, or enable runtime "
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_redaction_guard",
        description="Scan P3.4.2 rehearsal artifacts for unredacted PostgreSQL passwords.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Artifact file to scan. Repeat for every JSON/Markdown handoff file.",
    )
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless all artifacts are redaction-clean.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_redaction_guard_report(artifacts=args.artifact)
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_artifact_handoff"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
