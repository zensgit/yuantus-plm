#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
import shutil


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Error reading JSON artifact {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing JSON artifact {path}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a formal shared-dev 142 readonly refreeze proposal from a stable candidate preview."
    )
    parser.add_argument(
        "candidate_preview_dir",
        help="Directory produced by run_p2_shared_dev_142_refreeze_candidate.sh",
    )
    parser.add_argument(
        "--output-dir",
        help="Output proposal directory. Default: <candidate_preview_dir>/proposal",
    )
    parser.add_argument(
        "--output-md",
        help="Output markdown path. Default: <candidate_preview_dir>/REFREEZE_PROPOSAL.md",
    )
    parser.add_argument(
        "--output-json",
        help="Output JSON path. Default: <candidate_preview_dir>/refreeze_proposal.json",
    )
    parser.add_argument(
        "--proposed-label",
        default=f"shared-dev-142-readonly-{date.today().strftime('%Y%m%d')}",
        help="Proposed tracked baseline label.",
    )
    return parser.parse_args()


def render_markdown(payload: dict) -> str:
    excluded = "\n".join(
        f"| `{row['approval_id']}` | `{row['eco_name']}` | `{row['stage_name']}` | `{row['approval_deadline']}` |"
        for row in payload["excluded_pending_items"]
    )
    if not excluded:
        excluded = "| _(none)_ | `-` | `-` | `-` |"

    current = payload["current_official"]
    proposed = payload["proposed_candidate"]
    files = "\n".join(f"- `{path}`" for path in payload["update_targets"])
    proposal_artifacts = "\n".join(
        f"- `{path}`" for path in payload["proposal_artifacts"]
    )

    return f"""# Shared-dev 142 Readonly Refreeze Proposal

日期：{date.today().isoformat()}
verdict：{payload['verdict']}
proposal_ready：{str(payload['proposal_ready']).lower()}

## Source

- candidate_preview_dir: `{payload['candidate_preview_dir']}`
- current official label: `{current['baseline_label']}`
- proposed label: `{payload['proposed_label']}`
- proposed tracked dir: `{payload['proposed_tracked_dir']}`

## Decision

- kind: `{payload['decision']['kind']}`
- summary: {payload['decision']['summary']}

## Excluded Future Pending Items

| approval_id | eco_name | stage_name | approval_deadline |
|---|---|---|---|
{excluded}

## Count Summary

| Metric | current official | proposed candidate | Δ |
|---|---:|---:|---:|
| `items_count` | {current['items_count']} | {proposed['items_count']} | {proposed['items_count'] - current['items_count']} |
| `pending_count` | {current['pending_count']} | {proposed['pending_count']} | {proposed['pending_count'] - current['pending_count']} |
| `overdue_count` | {current['overdue_count']} | {proposed['overdue_count']} | {proposed['overdue_count'] - current['overdue_count']} |
| `escalated_count` | {current['escalated_count']} | {proposed['escalated_count']} | {proposed['escalated_count'] - current['escalated_count']} |
| `total_anomalies` | {current['total_anomalies']} | {proposed['total_anomalies']} | {proposed['total_anomalies'] - current['total_anomalies']} |

## Proposal Artifacts

{proposal_artifacts}

## Suggested Update Targets

{files}

## Notes

- This helper still does **not** switch the tracked baseline automatically.
- It materializes a concrete proposal pack from the accepted stable candidate so the later baseline switch is explicit and reviewable.
"""


def safe_rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    candidate_preview_dir = Path(args.candidate_preview_dir).resolve()
    candidate_json_path = candidate_preview_dir / "stable_readonly_candidate.json"
    candidate_dir = candidate_preview_dir / "candidate"

    payload = load_json(candidate_json_path)
    if not isinstance(payload, dict):
        raise SystemExit("stable_readonly_candidate.json must be an object")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else candidate_preview_dir / "proposal"
    output_md = Path(args.output_md).resolve() if args.output_md else candidate_preview_dir / "REFREEZE_PROPOSAL.md"
    output_json = Path(args.output_json).resolve() if args.output_json else candidate_preview_dir / "refreeze_proposal.json"

    proposed_label = args.proposed_label
    proposed_tracked_dir = f"./artifacts/p2-observation/{proposed_label}"
    proposal_baseline_dir = output_dir / proposed_label

    output_dir.mkdir(parents=True, exist_ok=True)
    if proposal_baseline_dir.exists():
        shutil.rmtree(proposal_baseline_dir)
    shutil.copytree(candidate_dir, proposal_baseline_dir)

    proposal_ready = bool(payload.get("candidate_ready")) and payload.get("decision", {}).get("kind") == "overdue-only-stable-candidate"
    verdict = "PASS" if proposal_ready else "FAIL"

    proposed_counts = payload.get("candidate_counts", {})
    current_counts = payload.get("current_counts", {})
    current_label = "shared-dev-142-readonly-20260421"

    result = {
        "verdict": verdict,
        "proposal_ready": proposal_ready,
        "candidate_preview_dir": str(candidate_preview_dir),
        "candidate_json": str(candidate_json_path),
        "candidate_dir": str(candidate_dir),
        "proposed_label": proposed_label,
        "proposed_tracked_dir": proposed_tracked_dir,
        "current_official": {
            "baseline_label": current_label,
            **current_counts,
        },
        "proposed_candidate": proposed_counts,
        "excluded_pending_items": payload.get("excluded_pending_items", []),
        "decision": {
            "kind": "proposal-ready" if proposal_ready else "candidate-not-ready",
            "summary": (
                "Stable candidate is ready to be reviewed as the next tracked readonly baseline proposal."
                if proposal_ready
                else "Stable candidate is not ready; do not prepare a tracked baseline switch yet."
            ),
        },
        "proposal_artifacts": [
            safe_rel(output_md, candidate_preview_dir),
            safe_rel(output_json, candidate_preview_dir),
            safe_rel(proposal_baseline_dir, candidate_preview_dir),
        ],
        "update_targets": [
            "scripts/run_p2_shared_dev_142_readonly_rerun.sh",
            "scripts/run_p2_shared_dev_142_workflow_readonly_check.sh",
            "scripts/run_p2_shared_dev_142_drift_audit.sh",
            "scripts/run_p2_shared_dev_142_drift_investigation.sh",
            "scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh",
            "docs/P2_SHARED_DEV_142_READONLY_RERUN_CHECKLIST.md",
            "docs/P2_SHARED_DEV_142_READONLY_REFREEZE_CANDIDATE_CHECKLIST.md",
            "docs/P2_SHARED_DEV_142_READONLY_REFREEZE_READINESS_CHECKLIST.md",
        ],
    }

    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
