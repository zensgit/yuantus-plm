from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from yuantus.scripts.tenant_import_rehearsal_handoff import (
    SCHEMA_VERSION as HANDOFF_SCHEMA_VERSION,
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


SCHEMA_VERSION = "p3.4.2-import-rehearsal-next-action-v1"


def _read_optional_json(path: str | Path | None) -> tuple[dict[str, Any] | None, str]:
    if not path:
        return None, ""
    json_path = Path(path)
    if not json_path.is_file():
        return None, f"{json_path} does not exist"
    value = json.loads(json_path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{json_path} must contain a JSON object")
    return value, ""


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _basic_context(*reports: dict[str, Any] | None) -> dict[str, str]:
    context = {
        "tenant_id": "",
        "target_schema": "",
        "target_url": "",
        "dry_run_json": "",
        "readiness_json": "",
        "handoff_json": "",
        "plan_json": "",
        "source_preflight_json": "",
        "target_preflight_json": "",
    }
    for report in reports:
        if not report:
            continue
        for key in (
            "tenant_id",
            "target_schema",
            "target_url",
            "dry_run_json",
            "readiness_json",
            "handoff_json",
            "plan_json",
            "source_preflight_json",
            "target_preflight_json",
        ):
            value = report.get(key)
            if isinstance(value, str) and value and not context[key]:
                context[key] = value
        checks = report.get("checks")
        if isinstance(checks, dict):
            dry_run_json = checks.get("dry_run_json")
            if isinstance(dry_run_json, str) and dry_run_json:
                context["dry_run_json"] = context["dry_run_json"] or dry_run_json
    return context


def build_next_action_report(
    *,
    dry_run_json: str | Path | None = None,
    readiness_json: str | Path | None = None,
    handoff_json: str | Path | None = None,
    plan_json: str | Path | None = None,
    source_preflight_json: str | Path | None = None,
    target_preflight_json: str | Path | None = None,
) -> dict[str, Any]:
    dry_run, dry_run_error = _read_optional_json(dry_run_json)
    readiness, readiness_error = _read_optional_json(readiness_json)
    handoff, handoff_error = _read_optional_json(handoff_json)
    import_plan, plan_error = _read_optional_json(plan_json)
    source_preflight, source_preflight_error = _read_optional_json(
        source_preflight_json
    )
    target_preflight, target_preflight_error = _read_optional_json(
        target_preflight_json
    )

    blockers: list[str] = []
    next_action = "ask_claude_to_implement_importer"
    claude_required = False

    if dry_run_error:
        blockers.append(dry_run_error)
    if readiness_error:
        blockers.append(readiness_error)
    if handoff_error:
        blockers.append(handoff_error)
    if plan_error:
        blockers.append(plan_error)
    if source_preflight_error:
        blockers.append(source_preflight_error)
    if target_preflight_error:
        blockers.append(target_preflight_error)

    if dry_run is None:
        next_action = "run_p3_4_1_dry_run"
        blockers.append("missing P3.4.1 dry-run report")
    elif dry_run.get("schema_version") != DRY_RUN_SCHEMA_VERSION:
        next_action = "fix_dry_run_report"
        blockers.append(f"dry-run schema_version must be {DRY_RUN_SCHEMA_VERSION}")
    elif dry_run.get("ready_for_import") is not True:
        next_action = "fix_dry_run_blockers"
        blockers.extend(_as_list(dry_run.get("blockers")))
        if not dry_run.get("blockers"):
            blockers.append("dry-run report must have ready_for_import=true")
    elif readiness is None:
        next_action = "collect_stop_gate_inputs_and_run_readiness"
        blockers.append("missing P3.4.2 readiness report")
    elif readiness.get("schema_version") != READINESS_SCHEMA_VERSION:
        next_action = "fix_readiness_report"
        blockers.append(f"readiness schema_version must be {READINESS_SCHEMA_VERSION}")
    elif readiness.get("ready_for_rehearsal") is not True:
        next_action = "fix_readiness_blockers"
        blockers.extend(_as_list(readiness.get("blockers")))
        if not readiness.get("blockers"):
            blockers.append("readiness report must have ready_for_rehearsal=true")
    elif handoff is None:
        next_action = "run_claude_handoff"
        blockers.append("missing Claude handoff report")
    elif handoff.get("schema_version") != HANDOFF_SCHEMA_VERSION:
        next_action = "fix_claude_handoff_report"
        blockers.append(f"handoff schema_version must be {HANDOFF_SCHEMA_VERSION}")
    elif handoff.get("ready_for_claude") is not True:
        next_action = "fix_claude_handoff_blockers"
        blockers.extend(_as_list(handoff.get("blockers")))
        if not handoff.get("blockers"):
            blockers.append("handoff report must have ready_for_claude=true")
    elif import_plan is None:
        next_action = "run_import_plan"
        blockers.append("missing import rehearsal plan report")
    elif import_plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        next_action = "fix_import_plan_report"
        blockers.append(f"import plan schema_version must be {PLAN_SCHEMA_VERSION}")
    elif import_plan.get("ready_for_importer") is not True:
        next_action = "fix_import_plan_blockers"
        blockers.extend(_as_list(import_plan.get("blockers")))
        if not import_plan.get("blockers"):
            blockers.append("import plan report must have ready_for_importer=true")
    elif source_preflight is None:
        next_action = "run_source_preflight"
        blockers.append("missing source preflight report")
    elif source_preflight.get("schema_version") != SOURCE_PREFLIGHT_SCHEMA_VERSION:
        next_action = "fix_source_preflight_report"
        blockers.append(
            f"source preflight schema_version must be {SOURCE_PREFLIGHT_SCHEMA_VERSION}"
        )
    elif source_preflight.get("ready_for_importer_source") is not True:
        next_action = "fix_source_preflight_blockers"
        blockers.extend(_as_list(source_preflight.get("blockers")))
        if not source_preflight.get("blockers"):
            blockers.append(
                "source preflight report must have ready_for_importer_source=true"
            )
    elif target_preflight is None:
        next_action = "run_target_preflight"
        blockers.append("missing target preflight report")
    elif target_preflight.get("schema_version") != TARGET_PREFLIGHT_SCHEMA_VERSION:
        next_action = "fix_target_preflight_report"
        blockers.append(
            f"target preflight schema_version must be {TARGET_PREFLIGHT_SCHEMA_VERSION}"
        )
    elif target_preflight.get("ready_for_importer_target") is not True:
        next_action = "fix_target_preflight_blockers"
        blockers.extend(_as_list(target_preflight.get("blockers")))
        if not target_preflight.get("blockers"):
            blockers.append(
                "target preflight report must have ready_for_importer_target=true"
            )
    else:
        claude_required = True

    return {
        "schema_version": SCHEMA_VERSION,
        "next_action": next_action,
        "claude_required": claude_required,
        "context": _basic_context(
            dry_run,
            readiness,
            handoff,
            import_plan,
            source_preflight,
            target_preflight,
        ),
        "inputs": {
            "dry_run_json": str(dry_run_json or ""),
            "readiness_json": str(readiness_json or ""),
            "handoff_json": str(handoff_json or ""),
            "plan_json": str(plan_json or ""),
            "source_preflight_json": str(source_preflight_json or ""),
            "target_preflight_json": str(target_preflight_json or ""),
        },
        "blockers": blockers,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    blockers = report["blockers"] or ["None"]
    context = report["context"]
    lines = [
        "# Tenant Import Rehearsal Next Action",
        "",
        f"- Schema version: `{report['schema_version']}`",
        f"- Next action: `{report['next_action']}`",
        f"- Claude required: `{str(report['claude_required']).lower()}`",
        f"- Tenant ID: `{context['tenant_id']}`",
        f"- Target schema: `{context['target_schema']}`",
        f"- Target URL: `{context['target_url']}`",
        f"- Dry-run JSON: `{context['dry_run_json'] or report['inputs']['dry_run_json']}`",
        f"- Readiness JSON: `{context['readiness_json'] or report['inputs']['readiness_json']}`",
        f"- Handoff JSON: `{context['handoff_json'] or report['inputs']['handoff_json']}`",
        f"- Plan JSON: `{context['plan_json'] or report['inputs']['plan_json']}`",
        "- Source preflight JSON: "
        f"`{context['source_preflight_json'] or report['inputs']['source_preflight_json']}`",
        "- Target preflight JSON: "
        f"`{context['target_preflight_json'] or report['inputs']['target_preflight_json']}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in blockers)
    lines.extend(
        [
            "",
            "## Operator Rule",
            "",
            "Notify the user to ask Claude to implement "
            "`yuantus.scripts.tenant_import_rehearsal` only when both "
            "`Claude required` is `true` and `Next action` is "
            "`ask_claude_to_implement_importer`.",
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
        prog="python -m yuantus.scripts.tenant_import_rehearsal_next_action",
        description="Summarize the next P3.4.2 action and whether Claude should start.",
    )
    parser.add_argument("--dry-run-json")
    parser.add_argument("--readiness-json")
    parser.add_argument("--handoff-json")
    parser.add_argument("--plan-json")
    parser.add_argument("--source-preflight-json")
    parser.add_argument("--target-preflight-json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 unless Claude is required now.",
    )
    args = parser.parse_args(argv)

    try:
        report = build_next_action_report(
            dry_run_json=args.dry_run_json,
            readiness_json=args.readiness_json,
            handoff_json=args.handoff_json,
            plan_json=args.plan_json,
            source_preflight_json=args.source_preflight_json,
            target_preflight_json=args.target_preflight_json,
        )
        _write_json(Path(args.output_json), report)
        _write_markdown(Path(args.output_md), report)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.strict and not report["claude_required"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
