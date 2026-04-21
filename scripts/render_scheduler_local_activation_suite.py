#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Error reading JSON artifact {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing JSON artifact {path}: {exc}") from exc


def expect_file(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Missing required artifact: {path}")


def step_ok(payload: dict[str, Any]) -> bool:
    return payload.get("ok") is True and not payload.get("errors")


def extract_enqueued_task(tick: dict[str, Any]) -> dict[str, Any]:
    enqueued = tick.get("enqueued") or []
    if not enqueued:
        return {}
    return enqueued[0] if isinstance(enqueued[0], dict) else {}


def build_payload(result_dir: Path) -> dict[str, Any]:
    result_dir = result_dir.resolve()

    paths = {
        "suite_validation": result_dir / "suite_validation.json",
        "dry_run_validation": result_dir / "01-dry-run-preflight" / "validation.json",
        "dry_run_scheduler": result_dir / "01-dry-run-preflight" / "scheduler_dry_run.json",
        "audit_validation": result_dir / "02-audit-retention-activation" / "validation.json",
        "audit_tick": result_dir / "02-audit-retention-activation" / "scheduler_tick.json",
        "audit_summary": result_dir / "02-audit-retention-activation" / "post_worker_summary.json",
        "eco_validation": result_dir / "03-eco-escalation-activation" / "validation.json",
        "eco_tick": result_dir / "03-eco-escalation-activation" / "scheduler_tick.json",
        "eco_before_summary": result_dir / "03-eco-escalation-activation" / "before_summary.json",
        "eco_after_summary": result_dir / "03-eco-escalation-activation" / "after_summary.json",
        "eco_before_anomalies": result_dir / "03-eco-escalation-activation" / "before_anomalies.json",
        "eco_after_anomalies": result_dir / "03-eco-escalation-activation" / "after_anomalies.json",
        "eco_summary": result_dir / "03-eco-escalation-activation" / "post_worker_summary.json",
    }
    for path in paths.values():
        expect_file(path)

    suite_validation = load_json(paths["suite_validation"])
    dry_run_validation = load_json(paths["dry_run_validation"])
    dry_run_scheduler = load_json(paths["dry_run_scheduler"])
    audit_validation = load_json(paths["audit_validation"])
    audit_tick = load_json(paths["audit_tick"])
    audit_summary = load_json(paths["audit_summary"])
    eco_validation = load_json(paths["eco_validation"])
    eco_tick = load_json(paths["eco_tick"])
    eco_before_summary = load_json(paths["eco_before_summary"])
    eco_after_summary = load_json(paths["eco_after_summary"])
    eco_before_anomalies = load_json(paths["eco_before_anomalies"])
    eco_after_anomalies = load_json(paths["eco_after_anomalies"])
    eco_summary = load_json(paths["eco_summary"])

    audit_job = extract_enqueued_task(audit_tick)
    eco_job = extract_enqueued_task(eco_tick)
    audit_worker_job = (audit_summary.get("jobs") or [{}])[0]
    eco_worker_job = (eco_summary.get("jobs") or [{}])[0]

    before_overdue_not = len(eco_before_anomalies.get("overdue_not_escalated") or [])
    after_overdue_not = len(eco_after_anomalies.get("overdue_not_escalated") or [])
    before_unresolved = len(eco_before_anomalies.get("escalated_unresolved") or [])
    after_unresolved = len(eco_after_anomalies.get("escalated_unresolved") or [])
    dry_run_tasks = sorted(item.get("task_type") for item in dry_run_scheduler.get("would_enqueue") or [])
    expected_dry_run_tasks = ["audit_retention_prune", "eco_approval_escalation"]

    checks = {
        "suite_ok": step_ok(suite_validation),
        "dry_run_ok": step_ok(dry_run_validation),
        "dry_run_no_enqueue": not (dry_run_scheduler.get("enqueued") or []),
        "dry_run_job_count_unchanged": dry_run_validation.get("job_count_before") == dry_run_validation.get("job_count_after"),
        "dry_run_would_enqueue_expected_tasks": dry_run_tasks == expected_dry_run_tasks,
        "audit_ok": step_ok(audit_validation),
        "audit_task_type": audit_job.get("task_type") == "audit_retention_prune",
        "audit_job_completed": audit_worker_job.get("status") == "completed",
        "audit_deleted_two_rows": (audit_worker_job.get("payload_result") or {}).get("deleted") == 2,
        "audit_kept_one_new_row": audit_summary.get("audit_count_after") == 1,
        "audit_kept_expected_path": audit_summary.get("audit_paths_after") == ["/scheduler-smoke/new-c"],
        "eco_ok": step_ok(eco_validation),
        "eco_task_type": eco_job.get("task_type") == "eco_approval_escalation",
        "eco_job_completed": eco_worker_job.get("status") == "completed",
        "eco_escalated_one": (eco_worker_job.get("payload_result") or {}).get("escalated") == 1,
        "eco_summary_delta": (
            eco_before_summary.get("pending_count") == 1
            and eco_before_summary.get("overdue_count") == 2
            and eco_before_summary.get("escalated_count") == 0
            and eco_after_summary.get("pending_count") == 1
            and eco_after_summary.get("overdue_count") == 3
            and eco_after_summary.get("escalated_count") == 1
        ),
        "eco_overdue_not_escalated_delta": before_overdue_not == 2 and after_overdue_not == 1,
        "eco_escalated_unresolved_delta": before_unresolved == 0 and after_unresolved == 1,
        "eco_admin_escalation_approval_count": eco_summary.get("admin_escalation_approval_count") == 1,
        "eco_approval_request_count": eco_summary.get("approval_request_count") == 2,
    }

    return {
        "result_dir": str(result_dir),
        "date": date.today().isoformat(),
        "ok": all(checks.values()),
        "checks": checks,
        "dry_run": {
            "would_enqueue_count": dry_run_validation.get("would_enqueue_count"),
            "job_count_before": dry_run_validation.get("job_count_before"),
            "job_count_after": dry_run_validation.get("job_count_after"),
            "would_enqueue_tasks": dry_run_tasks,
        },
        "audit_retention": {
            "job_id": audit_job.get("job_id"),
            "task_type": audit_job.get("task_type"),
            "job_status": audit_worker_job.get("status"),
            "worker_id": audit_worker_job.get("worker_id"),
            "deleted": (audit_worker_job.get("payload_result") or {}).get("deleted"),
            "audit_count_after": audit_summary.get("audit_count_after"),
            "audit_paths_after": audit_summary.get("audit_paths_after"),
        },
        "eco_escalation": {
            "job_id": eco_job.get("job_id"),
            "task_type": eco_job.get("task_type"),
            "job_status": eco_worker_job.get("status"),
            "worker_id": eco_worker_job.get("worker_id"),
            "escalated": (eco_worker_job.get("payload_result") or {}).get("escalated"),
            "before_summary": {
                "pending_count": eco_before_summary.get("pending_count"),
                "overdue_count": eco_before_summary.get("overdue_count"),
                "escalated_count": eco_before_summary.get("escalated_count"),
            },
            "after_summary": {
                "pending_count": eco_after_summary.get("pending_count"),
                "overdue_count": eco_after_summary.get("overdue_count"),
                "escalated_count": eco_after_summary.get("escalated_count"),
            },
            "before_overdue_not_escalated": before_overdue_not,
            "after_overdue_not_escalated": after_overdue_not,
            "before_escalated_unresolved": before_unresolved,
            "after_escalated_unresolved": after_unresolved,
            "admin_escalation_approval_count": eco_summary.get("admin_escalation_approval_count"),
            "approval_request_count": eco_summary.get("approval_request_count"),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    verdict = "PASS" if payload["ok"] else "FAIL"
    checks = payload["checks"]
    check_rows = "\n".join(
        f"| `{name}` | {'PASS' if value else 'FAIL'} |" for name, value in checks.items()
    )

    dry_run = payload["dry_run"]
    audit = payload["audit_retention"]
    eco = payload["eco_escalation"]

    return f"""# Scheduler Local Activation Suite Report

date: `{payload['date']}`
verdict: `{verdict}`
result_dir: `{payload['result_dir']}`

## Scope

This report summarizes local-dev-only scheduler activation evidence.

It does not enable scheduler on shared-dev 142 or production.

## Checks

| check | result |
|---|---|
{check_rows}

## Dry-run Preflight

- would_enqueue_count: `{dry_run['would_enqueue_count']}`
- job_count_before: `{dry_run['job_count_before']}`
- job_count_after: `{dry_run['job_count_after']}`
- would_enqueue_tasks: `{', '.join(dry_run['would_enqueue_tasks'])}`

## Audit Retention Activation

- job_id: `{audit['job_id']}`
- task_type: `{audit['task_type']}`
- job_status: `{audit['job_status']}`
- worker_id: `{audit['worker_id']}`
- deleted: `{audit['deleted']}`
- audit_count_after: `{audit['audit_count_after']}`
- audit_paths_after: `{audit['audit_paths_after']}`

## ECO Escalation Activation

- job_id: `{eco['job_id']}`
- task_type: `{eco['task_type']}`
- job_status: `{eco['job_status']}`
- worker_id: `{eco['worker_id']}`
- escalated: `{eco['escalated']}`
- summary before: `pending={eco['before_summary']['pending_count']}`, `overdue={eco['before_summary']['overdue_count']}`, `escalated={eco['before_summary']['escalated_count']}`
- summary after: `pending={eco['after_summary']['pending_count']}`, `overdue={eco['after_summary']['overdue_count']}`, `escalated={eco['after_summary']['escalated_count']}`
- overdue_not_escalated: `{eco['before_overdue_not_escalated']} -> {eco['after_overdue_not_escalated']}`
- escalated_unresolved: `{eco['before_escalated_unresolved']} -> {eco['after_escalated_unresolved']}`
- admin_escalation_approval_count: `{eco['admin_escalation_approval_count']}`
- approval_request_count: `{eco['approval_request_count']}`

## Decision

- PASS means the local scheduler dry-run, audit-retention activation, and ECO escalation activation evidence is internally consistent.
- FAIL means inspect the child `validation.json` files before using this suite as merge evidence.

## Artifacts

- `suite_validation.json`
- `01-dry-run-preflight/validation.json`
- `02-audit-retention-activation/validation.json`
- `03-eco-escalation-activation/validation.json`
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Markdown report from scripts/run_scheduler_local_activation_suite.sh artifacts."
    )
    parser.add_argument("result_dir", help="Scheduler local activation suite output directory")
    parser.add_argument(
        "--output-md",
        metavar="SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md",
        help="Output markdown path. Default: <result_dir>/SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md",
    )
    parser.add_argument(
        "--output-json",
        help="Output JSON path. Default: <result_dir>/scheduler_local_activation_suite_report.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_dir = Path(args.result_dir).resolve()
    payload = build_payload(result_dir)
    output_md = (
        Path(args.output_md).resolve()
        if args.output_md
        else result_dir / "SCHEDULER_LOCAL_ACTIVATION_SUITE_REPORT.md"
    )
    output_json = (
        Path(args.output_json).resolve()
        if args.output_json
        else result_dir / "scheduler_local_activation_suite_report.json"
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_md)
    print(output_json)
    if not payload["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
