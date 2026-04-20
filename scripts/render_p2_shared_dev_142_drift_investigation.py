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


def classify_drift(changed_metrics: list[dict], added_ids: list[str], removed_ids: list[str]) -> str:
    has_metric_drift = bool(changed_metrics)
    has_membership_drift = bool(added_ids or removed_ids)
    if not has_metric_drift and not has_membership_drift:
        return "no-drift"
    if has_metric_drift and has_membership_drift:
        return "mixed-drift"
    if has_membership_drift:
        return "membership-drift"
    return "state-drift"


def render_markdown(
    payload: dict,
    output_dir: Path,
) -> str:
    evidence_paths = payload["evidence_paths"]
    candidate_write_sources = payload["candidate_write_sources"]
    changed_metrics = payload["changed_metrics"]
    added_ids = payload["added_approval_ids"]
    removed_ids = payload["removed_approval_ids"]

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

    source_lines = "\n".join(
        f"- `{entry['path']}`: {entry['reason']}" for entry in candidate_write_sources
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

## Evidence Pack

{evidence_lines}

## Candidate Write Sources To Inspect

{source_lines}

## Interpretation

- `state-drift`: same approval population, but states or anomaly counts changed
- `membership-drift`: approval ids changed, which implies the observed set changed
- `mixed-drift`: both membership and state changed

## Next

- first confirm whether any operator intentionally used `auto-assign` or `escalate-overdue`
- then inspect service/router/task paths listed above before any readonly refreeze
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
    classification = classify_drift(changed_metrics, added_ids, removed_ids)

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

    payload = {
        "verdict": drift_audit.get("verdict", "FAIL"),
        "classification": classification,
        "baseline_label": drift_audit.get("baseline_label"),
        "current_label": drift_audit.get("current_label"),
        "drift_audit_dir": str(drift_audit_dir),
        "changed_metrics": changed_metrics,
        "added_approval_ids": added_ids,
        "removed_approval_ids": removed_ids,
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
