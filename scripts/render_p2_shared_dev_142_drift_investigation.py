#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Error reading JSON artifact {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing JSON artifact {path}: {exc}") from exc


def classify_drift(changed_metrics: list[dict], added_ids: list[str], removed_ids: list[str], *, is_time_drift: bool) -> str:
    has_metric_drift = bool(changed_metrics)
    has_membership_drift = bool(added_ids or removed_ids)
    if not has_metric_drift and not has_membership_drift:
        return "no-drift"
    if has_metric_drift and has_membership_drift:
        return "mixed-drift"
    if has_membership_drift:
        return "membership-drift"
    if is_time_drift:
        return "time-drift"
    return "state-drift"


def load_json_if_exists(path: Path):
    if not path.is_file():
        return None
    return load_json(path)


def build_item_change_rows(
    baseline_items: list[dict] | None,
    current_items: list[dict] | None,
) -> list[dict]:
    if not isinstance(baseline_items, list) or not isinstance(current_items, list):
        return []

    baseline_by_id = {
        entry.get("approval_id"): entry
        for entry in baseline_items
        if isinstance(entry, dict) and entry.get("approval_id")
    }
    current_by_id = {
        entry.get("approval_id"): entry
        for entry in current_items
        if isinstance(entry, dict) and entry.get("approval_id")
    }

    rows: list[dict] = []
    for approval_id in sorted(set(baseline_by_id) & set(current_by_id)):
        baseline = baseline_by_id[approval_id]
        current = current_by_id[approval_id]
        changed_fields = [
            field
            for field in sorted(set(baseline) | set(current))
            if baseline.get(field) != current.get(field)
        ]
        if not changed_fields:
            continue
        rows.append(
            {
                "approval_id": approval_id,
                "eco_id": current.get("eco_id", baseline.get("eco_id")),
                "eco_name": current.get("eco_name", baseline.get("eco_name")),
                "stage_id": current.get("stage_id", baseline.get("stage_id")),
                "stage_name": current.get("stage_name", baseline.get("stage_name")),
                "approval_deadline": current.get("approval_deadline", baseline.get("approval_deadline")),
                "baseline_is_overdue": baseline.get("is_overdue"),
                "current_is_overdue": current.get("is_overdue"),
                "baseline_hours_overdue": baseline.get("hours_overdue"),
                "current_hours_overdue": current.get("hours_overdue"),
                "changed_fields": changed_fields,
                "baseline": {field: baseline.get(field) for field in changed_fields},
                "current": {field: current.get(field) for field in changed_fields},
            }
        )
    return rows


def analyze_time_drift(
    *,
    changed_metrics: list[dict],
    added_ids: list[str],
    removed_ids: list[str],
    approval_change_rows: list[dict],
) -> dict:
    if added_ids or removed_ids or not approval_change_rows:
        return {
            "is_time_drift": False,
            "newly_overdue_ids": [],
            "aged_overdue_ids": [],
            "summary": "not-applicable",
        }

    allowed_metric_names = {"pending_count", "overdue_count", "total_anomalies", "overdue_not_escalated"}
    metric_names = {entry.get("metric") for entry in changed_metrics}
    if metric_names - allowed_metric_names:
        return {
            "is_time_drift": False,
            "newly_overdue_ids": [],
            "aged_overdue_ids": [],
            "summary": "metric-delta-outside-time-drift-envelope",
        }

    newly_overdue_ids: list[str] = []
    aged_overdue_ids: list[str] = []

    for row in approval_change_rows:
        fields = set(row["changed_fields"])
        if not fields <= {"is_overdue", "hours_overdue"}:
            return {
                "is_time_drift": False,
                "newly_overdue_ids": [],
                "aged_overdue_ids": [],
                "summary": f"approval {row['approval_id']} changed non-time fields: {sorted(fields)}",
            }

        baseline_overdue = bool(row.get("baseline_is_overdue", False))
        current_overdue = bool(row.get("current_is_overdue", False))

        if not current_overdue:
            return {
                "is_time_drift": False,
                "newly_overdue_ids": [],
                "aged_overdue_ids": [],
                "summary": f"approval {row['approval_id']} did not end in overdue state",
            }

        if baseline_overdue:
            aged_overdue_ids.append(row["approval_id"])
            continue

        if row.get("baseline_hours_overdue") is not None:
            return {
                "is_time_drift": False,
                "newly_overdue_ids": [],
                "aged_overdue_ids": [],
                "summary": f"approval {row['approval_id']} had unexpected baseline hours_overdue",
            }

        newly_overdue_ids.append(row["approval_id"])

    if not newly_overdue_ids:
        return {
            "is_time_drift": False,
            "newly_overdue_ids": [],
            "aged_overdue_ids": aged_overdue_ids,
            "summary": "no approval crossed from pending to overdue",
        }

    return {
        "is_time_drift": True,
        "newly_overdue_ids": newly_overdue_ids,
        "aged_overdue_ids": aged_overdue_ids,
        "summary": (
            f"{len(newly_overdue_ids)} approval(s) crossed their existing deadline while "
            f"{len(aged_overdue_ids)} already-overdue approval(s) simply accumulated more overdue hours."
        ),
    }


def render_markdown(
    payload: dict,
    output_dir: Path,
) -> str:
    evidence_paths = payload["evidence_paths"]
    candidate_write_sources = payload["candidate_write_sources"]
    changed_metrics = payload["changed_metrics"]
    added_ids = payload["added_approval_ids"]
    removed_ids = payload["removed_approval_ids"]
    approval_change_rows = payload["approval_change_rows"]
    likely_cause = payload["likely_cause"]
    time_drift_ids = payload["time_drift_approval_ids"]

    changed_rows = "\n".join(
        f"| `{entry['metric']}` | `{entry['baseline']}` | `{entry['current']}` | `{entry['delta']}` |"
        for entry in changed_metrics
    )
    if not changed_rows:
        changed_rows = "| _(none)_ | `-` | `-` | `0` |"

    def _fmt_ids(values: list[str]) -> str:
        if not values:
            return "- _(none)_"
        return "\n".join(f"- `{value}`" for value in values)

    evidence_lines = "\n".join(
        f"- `{name}`: `{path}`" for name, path in evidence_paths.items()
    )

    approval_change_lines = "\n".join(
        (
            f"| `{entry['approval_id']}` | `{entry['eco_name']}` | `{entry['stage_name']}` | "
            f"`{entry['approval_deadline']}` | "
            f"`{', '.join(entry['changed_fields'])}` |"
        )
        for entry in approval_change_rows
    )
    if not approval_change_lines:
        approval_change_lines = "| _(none)_ | `-` | `-` | `-` | `-` |"

    source_lines = "\n".join(
        f"- `{entry['path']}`: {entry['reason']}" for entry in candidate_write_sources
    )

    likely_cause_lines = "\n".join(
        [
            f"- kind: `{likely_cause['kind']}`",
            f"- summary: {likely_cause['summary']}",
            f"- approvals: {', '.join(f'`{approval_id}`' for approval_id in time_drift_ids) if time_drift_ids else '- _(none)_'}",
        ]
    )

    return f"""# Shared-dev 142 Drift Investigation

日期：{date.today().isoformat()}
verdict：{payload['verdict']}
classification：{payload['classification']}

## Scope

- drift_audit_dir: `{payload['drift_audit_dir']}`
- baseline_label: `{payload['baseline_label']}`
- current_label: `{payload['current_label']}`
- output_dir: `{output_dir}`

## Metric Drift

| metric | baseline | current | delta |
|---|---:|---:|---:|
{changed_rows}

## Approval ID Diff

### Added
{_fmt_ids(added_ids)}

### Removed
{_fmt_ids(removed_ids)}

## Likely Cause

{likely_cause_lines}

## Changed Approvals

| approval_id | eco_name | stage_name | approval_deadline | changed_fields |
|---|---|---|---|---|
{approval_change_lines}

## Evidence Pack

{evidence_lines}

## Candidate Write Sources To Inspect

{source_lines}

## Interpretation

- `time-drift`: same approval population, and one or more approvals simply crossed an existing deadline into overdue state
- `state-drift`: same approval population, but states or anomaly counts changed
- `membership-drift`: approval ids changed, which implies the observed set changed
- `mixed-drift`: both membership and state changed

## Next

- if this is `time-drift`, confirm no one intentionally enabled write smoke, then decide whether the readonly baseline simply aged out and should be refrozen
- if this is still `state-drift`, first confirm whether any operator intentionally used `auto-assign` or `escalate-overdue`
- only run readonly refreeze if the drift is understood and accepted
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a shared-dev 142 drift investigation evidence summary from a drift-audit result directory."
    )
    parser.add_argument("drift_audit_dir", help="Directory produced by run_p2_shared_dev_142_drift_audit.sh")
    parser.add_argument(
        "--output-md",
        help="Output markdown path. Default: <drift_audit_dir>/DRIFT_INVESTIGATION.md",
    )
    parser.add_argument(
        "--output-json",
        help="Output JSON path. Default: <drift_audit_dir>/drift_investigation.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    drift_audit_dir = Path(args.drift_audit_dir).resolve()
    drift_audit_path = drift_audit_dir / "drift_audit.json"
    if not drift_audit_path.is_file():
        raise SystemExit(f"Missing drift audit artifact: {drift_audit_path}")

    drift_audit = load_json(drift_audit_path)
    changed_metrics = drift_audit.get("changed_metrics", [])
    if not changed_metrics:
        metric_deltas = drift_audit.get("metric_deltas", {})
        changed_metrics = [
            {
                "metric": metric,
                "baseline": values.get("baseline"),
                "current": values.get("current"),
                "delta": values.get("delta"),
            }
            for metric, values in metric_deltas.items()
            if isinstance(values, dict)
        ]
    added_ids = drift_audit.get("added_approval_ids", [])
    removed_ids = drift_audit.get("removed_approval_ids", [])
    baseline_dir = Path(drift_audit["baseline_dir"]).resolve() if drift_audit.get("baseline_dir") else None
    current_dir = Path(drift_audit["current_dir"]).resolve() if drift_audit.get("current_dir") else None

    baseline_items = load_json_if_exists(baseline_dir / "items.json") if baseline_dir else None
    current_items = load_json_if_exists(current_dir / "items.json") if current_dir else None
    approval_change_rows = build_item_change_rows(baseline_items, current_items)
    time_drift_analysis = analyze_time_drift(
        changed_metrics=changed_metrics,
        added_ids=added_ids,
        removed_ids=removed_ids,
        approval_change_rows=approval_change_rows,
    )
    classification = classify_drift(
        changed_metrics,
        added_ids,
        removed_ids,
        is_time_drift=time_drift_analysis["is_time_drift"],
    )

    evidence_paths = {
        "precheck_markdown": "drift-audit/current-precheck/OBSERVATION_PRECHECK.md",
        "precheck_probe": "drift-audit/current-precheck/summary_probe.json",
        "result_markdown": "drift-audit/current/OBSERVATION_RESULT.md",
        "diff_markdown": "drift-audit/current/OBSERVATION_DIFF.md",
        "eval_markdown": "drift-audit/current/OBSERVATION_EVAL.md",
        "summary_json": "drift-audit/current/summary.json",
        "items_json": "drift-audit/current/items.json",
        "anomalies_json": "drift-audit/current/anomalies.json",
        "export_json": "drift-audit/current/export.json",
        "export_csv": "drift-audit/current/export.csv",
        "drift_audit_markdown": "drift-audit/DRIFT_AUDIT.md",
        "drift_audit_json": "drift-audit/drift_audit.json",
    }

    candidate_write_sources = [
        {
            "path": "src/yuantus/meta_engine/web/eco_router.py",
            "reason": "exposes the shared-dev write endpoints most likely to change readonly observation state: auto-assign approvers and escalate-overdue.",
        },
        {
            "path": "src/yuantus/meta_engine/services/eco_service.py",
            "reason": "implements auto-assign stage approvers and overdue escalation, the two highest-probability state transition sources for pending/overdue/escalated drift.",
        },
        {
            "path": "scripts/verify_p2_dev_observation_startup.sh",
            "reason": "optional write smoke can call auto-assign and escalate-overdue when RUN_WRITE_SMOKE=1, so check whether any manual smoke run enabled it.",
        },
        {
            "path": "scripts/seed_p2_observation_fixtures.py",
            "reason": "documents the expected seeded overdue/escalated counts and helps distinguish fixture expectations from later shared-dev writes.",
        },
    ]

    likely_cause = {
        "kind": "deadline-rollover" if time_drift_analysis["is_time_drift"] else "unknown",
        "summary": (
            time_drift_analysis["summary"]
            if time_drift_analysis["is_time_drift"]
            else "same approval population drifted, but the current evidence is not enough to rule out write-driven state changes"
        ),
    }

    payload = {
        "verdict": drift_audit.get("verdict", "FAIL"),
        "classification": classification,
        "baseline_label": drift_audit.get("baseline_label"),
        "current_label": drift_audit.get("current_label"),
        "drift_audit_dir": str(drift_audit_dir),
        "changed_metrics": changed_metrics,
        "added_approval_ids": added_ids,
        "removed_approval_ids": removed_ids,
        "approval_change_rows": approval_change_rows,
        "time_drift_approval_ids": time_drift_analysis["newly_overdue_ids"],
        "likely_cause": likely_cause,
        "baseline_metrics": drift_audit.get("baseline_metrics", {}),
        "current_metrics": drift_audit.get("current_metrics", {}),
        "evidence_paths": evidence_paths,
        "candidate_write_sources": candidate_write_sources,
    }

    output_md = Path(args.output_md).resolve() if args.output_md else drift_audit_dir / "DRIFT_INVESTIGATION.md"
    output_json = Path(args.output_json).resolve() if args.output_json else drift_audit_dir / "drift_investigation.json"
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    output_md.write_text(render_markdown(payload, drift_audit_dir.parent), encoding="utf-8")
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(output_md)
    print(output_json)


if __name__ == "__main__":
    main()
