from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts.tenant_import_rehearsal_handoff import (
    SCHEMA_VERSION as HANDOFF_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_import_rehearsal_next_action import (
    SCHEMA_VERSION as NEXT_ACTION_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_import_rehearsal_plan import (
    SCHEMA_VERSION as PLAN_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_import_rehearsal_readiness import (
    SCHEMA_VERSION as READINESS_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_import_rehearsal_source_preflight import (
    SCHEMA_VERSION as SOURCE_PREFLIGHT_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_import_rehearsal_target_preflight import (
    SCHEMA_VERSION as TARGET_PREFLIGHT_SCHEMA_VERSION,
)
from yuantus.scripts.tenant_migration_dry_run import SCHEMA_VERSION as DRY_RUN_SCHEMA_VERSION


SCHEMA_VERSION = "p3.4.2-importer-implementation-packet-v1"
FINAL_NEXT_ACTION = "ask_claude_to_implement_importer"
_ARTIFACT_RULES = {
    "dry_run_json": {
        "label": "dry-run",
        "schema_version": DRY_RUN_SCHEMA_VERSION,
        "ready_field": "ready_for_import",
    },
    "readiness_json": {
        "label": "readiness",
        "schema_version": READINESS_SCHEMA_VERSION,
        "ready_field": "ready_for_rehearsal",
    },
    "handoff_json": {
        "label": "handoff",
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "ready_field": "ready_for_claude",
    },
    "plan_json": {
        "label": "plan",
        "schema_version": PLAN_SCHEMA_VERSION,
        "ready_field": "ready_for_importer",
    },
    "source_preflight_json": {
        "label": "source preflight",
        "schema_version": SOURCE_PREFLIGHT_SCHEMA_VERSION,
        "ready_field": "ready_for_importer_source",
    },
    "target_preflight_json": {
        "label": "target preflight",
        "schema_version": TARGET_PREFLIGHT_SCHEMA_VERSION,
        "ready_field": "ready_for_importer_target",
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _artifact_path(
    *,
    key: str,
    context: dict[str, Any],
    inputs: dict[str, Any],
) -> str:
    return _as_str(context.get(key) or inputs.get(key))


def _read_artifact(path_text: str) -> tuple[dict[str, Any] | None, str]:
    path = Path(path_text)
    if not path.is_file():
        return None, f"{path_text} does not exist"
    try:
        return _read_json(path), ""
    except Exception as exc:
        return None, f"{path_text} is not a valid JSON artifact: {exc}"


def _validate_artifacts(
    *,
    context: dict[str, Any],
    inputs: dict[str, Any],
) -> tuple[dict[str, str], list[str], list[dict[str, Any]]]:
    paths: dict[str, str] = {}
    blockers: list[str] = []
    validations: list[dict[str, Any]] = []
    expected_tenant_id = _as_str(context.get("tenant_id"))
    expected_target_schema = _as_str(context.get("target_schema"))

    for key, rule in _ARTIFACT_RULES.items():
        path_text = _artifact_path(key=key, context=context, inputs=inputs)
        paths[key] = path_text
        label = str(rule["label"])
        expected_schema = str(rule["schema_version"])
        ready_field = str(rule["ready_field"])
        validation: dict[str, Any] = {
            "artifact": key,
            "path": path_text,
            "schema_version": "",
            "ready_field": ready_field,
            "ready": False,
        }

        if not path_text:
            blockers.append(f"next-action report missing {key}")
            validations.append(validation)
            continue

        artifact, read_error = _read_artifact(path_text)
        if read_error:
            blockers.append(f"{label} artifact {read_error}")
            validations.append(validation)
            continue

        assert artifact is not None
        actual_schema = _as_str(artifact.get("schema_version"))
        validation["schema_version"] = actual_schema
        validation["ready"] = artifact.get(ready_field) is True

        if actual_schema != expected_schema:
            blockers.append(f"{label} schema_version must be {expected_schema}")
        if artifact.get(ready_field) is not True:
            blockers.append(f"{label} artifact must have {ready_field}=true")
        if _as_list(artifact.get("blockers")):
            blockers.append(f"{label} artifact must have no blockers")

        tenant_id = _as_str(artifact.get("tenant_id"))
        target_schema = _as_str(artifact.get("target_schema"))
        if expected_tenant_id and tenant_id and tenant_id != expected_tenant_id:
            blockers.append(f"{label} tenant_id must match next-action context")
        if (
            expected_target_schema
            and target_schema
            and target_schema != expected_target_schema
        ):
            blockers.append(f"{label} target_schema must match next-action context")

        validations.append(validation)

    return paths, blockers, validations


def build_implementation_packet_report(
    next_action_json: str | Path,
    *,
    output_md: str | Path,
) -> dict[str, Any]:
    """Convert a green next-action report into a bounded Claude task packet."""
    next_action_path = Path(next_action_json)
    next_action = _read_json(next_action_path)
    context = _as_dict(next_action.get("context"))
    inputs = _as_dict(next_action.get("inputs"))

    blockers: list[str] = []
    if next_action.get("schema_version") != NEXT_ACTION_SCHEMA_VERSION:
        blockers.append(
            f"next-action schema_version must be {NEXT_ACTION_SCHEMA_VERSION}"
        )
    if next_action.get("next_action") != FINAL_NEXT_ACTION:
        blockers.append(f"next_action must be {FINAL_NEXT_ACTION}")
    if next_action.get("claude_required") is not True:
        blockers.append("next-action report must have claude_required=true")
    if _as_list(next_action.get("blockers")):
        blockers.append("next-action report must have no blockers")

    artifact_paths, artifact_blockers, artifact_validations = _validate_artifacts(
        context=context,
        inputs=inputs,
    )
    blockers.extend(artifact_blockers)

    return {
        "schema_version": SCHEMA_VERSION,
        "next_action_json": str(next_action_path),
        "next_action_schema_version": next_action.get("schema_version"),
        "ready_for_claude_importer": not blockers,
        "ready_for_cutover": False,
        "tenant_id": _as_str(context.get("tenant_id")),
        "target_schema": _as_str(context.get("target_schema")),
        "target_url": _as_str(context.get("target_url")),
        "dry_run_json": artifact_paths["dry_run_json"],
        "readiness_json": artifact_paths["readiness_json"],
        "handoff_json": artifact_paths["handoff_json"],
        "plan_json": artifact_paths["plan_json"],
        "source_preflight_json": artifact_paths["source_preflight_json"],
        "target_preflight_json": artifact_paths["target_preflight_json"],
        "artifact_validations": artifact_validations,
        "implementation_md": str(output_md),
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    ready = str(report["ready_for_claude_importer"]).lower()
    artifact_validations = report.get("artifact_validations") or []
    lines = [
        "# Claude Task - P3.4.2 Tenant Import Rehearsal Importer",
        "",
        f"- Packet schema: `{report['schema_version']}`",
        f"- Claude can implement importer: `{ready}`",
        f"- Ready for cutover: `{str(report['ready_for_cutover']).lower()}`",
        f"- Tenant ID: `{report['tenant_id']}`",
        f"- Target schema: `{report['target_schema']}`",
        f"- Target URL: `{report['target_url']}`",
        f"- Next-action JSON: `{report['next_action_json']}`",
        f"- Dry-run JSON: `{report['dry_run_json']}`",
        f"- Readiness JSON: `{report['readiness_json']}`",
        f"- Handoff JSON: `{report['handoff_json']}`",
        f"- Plan JSON: `{report['plan_json']}`",
        f"- Source preflight JSON: `{report['source_preflight_json']}`",
        f"- Target preflight JSON: `{report['target_preflight_json']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Artifact Integrity",
            "",
            "| Artifact | Schema version | Ready field | Ready | Path |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for validation in artifact_validations:
        lines.append(
            "| "
            f"`{validation['artifact']}` | "
            f"`{validation['schema_version']}` | "
            f"`{validation['ready_field']}` | "
            f"`{str(validation['ready']).lower()}` | "
            f"`{validation['path']}` |"
        )
    lines.extend(
        [
            "",
            "## Implementation Scope",
            "",
            "Implement `yuantus.scripts.tenant_import_rehearsal` only when "
            "`Claude can implement importer` is `true`.",
            "",
            "The importer must:",
            "",
            "- require `--confirm-rehearsal` before any DB connection;",
            "- require this implementation packet and validate it before any DB connection;",
            "- validate the next-action JSON before any DB connection;",
            "- validate the dry-run, readiness, handoff, plan, source preflight, "
            "and target preflight JSON before any DB connection;",
            "- connect to the source DB read-only;",
            "- connect only to the non-production PostgreSQL target DSN supplied by the operator;",
            "- import only tables from `tenant_tables_in_import_order`;",
            "- block every global/control-plane table;",
            "- compare target row counts with source expectations after import;",
            "- emit JSON and Markdown rehearsal reports;",
            "- keep `ready_for_cutover=false`.",
            "",
            "## Non-Goals",
            "",
            "- No production cutover.",
            "- No `TENANCY_MODE=schema-per-tenant` enablement.",
            "- No source writes.",
            "- No global/control-plane table import.",
            "- No schema creation or migration.",
            "- No automatic rollback or destructive cleanup.",
            "",
            "## Required Verification",
            "",
            "```bash",
            ".venv/bin/python -m pytest -q \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal.py \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \\",
            "  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py",
            "",
            ".venv/bin/python -m py_compile \\",
            "  src/yuantus/scripts/tenant_import_rehearsal.py \\",
            "  src/yuantus/scripts/tenant_import_rehearsal_implementation_packet.py",
            "",
            "git diff --check",
            "```",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_implementation_packet",
        description="Generate the final Claude implementation packet after all P3.4.2 gates are green.",
    )
    parser.add_argument("--next-action-json", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless the generated implementation packet is ready for Claude.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_implementation_packet_report(
            args.next_action_json,
            output_md=args.output_md,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["ready_for_claude_importer"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
