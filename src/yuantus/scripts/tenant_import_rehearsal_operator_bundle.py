from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts import tenant_import_rehearsal_operator_request as operator_request


SCHEMA_VERSION = "p3.4.2-tenant-import-rehearsal-operator-bundle-v1"


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


def _environment_checks(required_inputs: list[str]) -> list[str]:
    checks: list[str] = []
    if "SOURCE_DATABASE_URL environment variable" in required_inputs:
        checks.append('test -n "${SOURCE_DATABASE_URL:-}"')
    if "TARGET_DATABASE_URL environment variable" in required_inputs:
        checks.append('test -n "${TARGET_DATABASE_URL:-}"')
    return checks


def _bundle_commands(request_report: dict[str, Any]) -> list[dict[str, str]]:
    required_inputs = _as_list(request_report.get("required_operator_inputs"))
    commands: list[dict[str, str]] = [
        {
            "name": "safety_readme",
            "command": (
                "Read this bundle and confirm the target database is "
                "non-production before running any command."
            ),
        }
    ]
    for index, check in enumerate(_environment_checks(required_inputs), start=1):
        commands.append({"name": f"env_check_{index}", "command": check})

    next_command = _as_str(request_report.get("next_command"))
    if next_command:
        commands.append(
            {
                "name": _as_str(request_report.get("next_command_name")) or "next_command",
                "command": next_command,
            }
        )
    else:
        commands.append(
            {
                "name": "manual_review",
                "command": (
                    "No command is required from this bundle. Review the listed "
                    "artifacts and keep the production cutover gate closed."
                ),
            }
        )
    return commands


def build_operator_bundle_report(*, operator_request_json: str | Path) -> dict[str, Any]:
    """Build a DB-free operator bundle from a ready operator request."""
    request_path = Path(operator_request_json)
    request_report, read_error = _read_json_object(request_path)
    blockers: list[str] = []
    if read_error:
        request_report = {}
        blockers.append(f"operator request {read_error}")
    assert request_report is not None

    if request_report.get("schema_version") != operator_request.SCHEMA_VERSION:
        blockers.append(
            f"operator request schema_version must be {operator_request.SCHEMA_VERSION}"
        )
    if request_report.get("ready_for_operator_request") is not True:
        blockers.append("operator request must have ready_for_operator_request=true")
    if request_report.get("ready_for_cutover") is not False:
        blockers.append("operator request must have ready_for_cutover=false")
    if _as_list(request_report.get("blockers")):
        blockers.append("operator request must have no blockers")

    required_inputs = _as_list(request_report.get("required_operator_inputs"))
    commands = _bundle_commands(request_report)
    return {
        "schema_version": SCHEMA_VERSION,
        "operator_request_json": str(request_path),
        "operator_request_schema_version": request_report.get("schema_version", ""),
        "tenant_id": _as_str(request_report.get("tenant_id")),
        "target_schema": _as_str(request_report.get("target_schema")),
        "target_url": _as_str(request_report.get("target_url")),
        "current_stage": _as_str(request_report.get("current_stage")),
        "next_action": _as_str(request_report.get("next_action")),
        "next_command_name": _as_str(request_report.get("next_command_name")),
        "required_operator_inputs": required_inputs,
        "artifacts": request_report.get("artifacts") if isinstance(request_report.get("artifacts"), list) else [],
        "commands": commands,
        "ready_for_operator_bundle": not blockers,
        "ready_for_cutover": False,
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    required_inputs = report["required_operator_inputs"] or ["None"]
    lines = [
        "# Tenant Import Rehearsal Operator Bundle",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Ready for operator bundle: `{str(report['ready_for_operator_bundle']).lower()}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Current stage: `{report['current_stage']}`",
        f"- Next action: `{report['next_action']}`",
        f"- Next command name: `{report['next_command_name']}`",
        f"- Operator request JSON: `{report['operator_request_json']}`",
        "",
        "## Required Operator Inputs",
        "",
    ]
    lines.extend(f"- {item}" for item in required_inputs)
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(["", "## Commands", ""])
    for command in report["commands"]:
        lines.extend(
            [
                f"### {command['name']}",
                "",
                "```bash",
                command["command"],
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Artifact Summary",
            "",
            "| Artifact | Exists | Ready | Path |",
            "| --- | --- | --- | --- |",
        ]
    )
    for artifact in report["artifacts"]:
        if not isinstance(artifact, dict):
            continue
        lines.append(
            "| "
            f"`{_as_str(artifact.get('artifact'))}` | "
            f"`{str(artifact.get('exists') is True).lower()}` | "
            f"`{str(artifact.get('ready') is True).lower()}` | "
            f"`{_as_str(artifact.get('path'))}` |"
        )
    if not report["artifacts"]:
        lines.append("| None | `false` | `false` | `` |")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "This bundle reads a previously generated operator request only. It does "
            "not run commands, open database connections, accept evidence, build an "
            "archive, authorize production cutover, or enable runtime schema-per-tenant mode.",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_operator_bundle",
        description="Build a DB-free P3.4.2 operator bundle from an operator request.",
    )
    parser.add_argument("--operator-request-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the operator bundle is ready.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_operator_bundle_report(
            operator_request_json=args.operator_request_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_operator_bundle"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
