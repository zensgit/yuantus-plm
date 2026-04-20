#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Error reading JSON artifact {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing JSON artifact {path}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a stable readonly candidate pack for shared-dev 142 by excluding future-deadline pending approvals."
    )
    parser.add_argument("current_dir", help="Current observation result dir containing summary/items/anomalies/export artifacts")
    parser.add_argument("--output-dir", help="Output candidate artifact dir. Default: <current_dir>/../candidate")
    parser.add_argument("--output-md", help="Output markdown path. Default: <current_dir>/../STABLE_READONLY_CANDIDATE.md")
    parser.add_argument("--output-json", help="Output JSON path. Default: <current_dir>/../stable_readonly_candidate.json")
    parser.add_argument("--environment", default="shared-dev-142-stable-readonly-candidate", help="Environment label for nested OBSERVATION_RESULT.md")
    parser.add_argument("--operator", default="system", help="Operator label for nested OBSERVATION_RESULT.md")
    return parser.parse_args()


def aggregate_by_stage(items: list[dict]) -> list[dict]:
    rows: dict[tuple[str | None, str | None], dict] = {}
    for item in items:
        key = (item.get("stage_id"), item.get("stage_name"))
        row = rows.setdefault(
            key,
            {
                "stage_id": item.get("stage_id"),
                "stage_name": item.get("stage_name"),
                "pending": 0,
                "overdue": 0,
            },
        )
        if item.get("is_overdue", False):
            row["overdue"] += 1
        else:
            row["pending"] += 1
    return list(rows.values())


def aggregate_by_assignee(items: list[dict]) -> list[dict]:
    rows: dict[tuple[int | None, str | None], dict] = {}
    for item in items:
        key = (item.get("assignee_id"), item.get("assignee_username"))
        row = rows.setdefault(
            key,
            {
                "user_id": item.get("assignee_id"),
                "username": item.get("assignee_username"),
                "count": 0,
            },
        )
        row["count"] += 1
    return list(rows.values())


def build_summary(items: list[dict]) -> dict:
    return {
        "pending_count": sum(1 for item in items if not item.get("is_overdue", False)),
        "overdue_count": sum(1 for item in items if item.get("is_overdue", False)),
        "escalated_count": sum(1 for item in items if item.get("is_escalated", False)),
        "by_stage": aggregate_by_stage(items),
        "by_assignee": aggregate_by_assignee(items),
    }


def filter_entries(entries: list, excluded_approval_ids: set[str], excluded_eco_ids: set[str]) -> list:
    filtered: list = []
    for entry in entries:
        if not isinstance(entry, dict):
            filtered.append(entry)
            continue
        if entry.get("approval_id") in excluded_approval_ids:
            continue
        if entry.get("eco_id") in excluded_eco_ids:
            continue
        filtered.append(entry)
    return filtered


def build_anomalies(anomalies: dict, excluded_approval_ids: set[str], excluded_eco_ids: set[str]) -> dict:
    candidate = {
        "no_candidates": filter_entries(anomalies.get("no_candidates", []), excluded_approval_ids, excluded_eco_ids),
        "escalated_unresolved": filter_entries(anomalies.get("escalated_unresolved", []), excluded_approval_ids, excluded_eco_ids),
        "overdue_not_escalated": filter_entries(anomalies.get("overdue_not_escalated", []), excluded_approval_ids, excluded_eco_ids),
    }
    candidate["total_anomalies"] = (
        len(candidate["no_candidates"])
        + len(candidate["escalated_unresolved"])
        + len(candidate["overdue_not_escalated"])
    )
    return candidate


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if rows:
        fieldnames: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
    else:
        fieldnames = ["approval_id"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_top_markdown(payload: dict) -> str:
    excluded_rows = "\n".join(
        (
            f"| `{entry['approval_id']}` | `{entry['eco_name']}` | `{entry['stage_name']}` | "
            f"`{entry['approval_deadline']}` | `{entry['assignee_username']}` |"
        )
        for entry in payload["excluded_pending_items"]
    )
    if not excluded_rows:
        excluded_rows = "| _(none)_ | `-` | `-` | `-` | `-` |"

    current = payload["current_counts"]
    candidate = payload["candidate_counts"]

    return f"""# Shared-dev 142 Stable Readonly Candidate

日期：{date.today().isoformat()}
verdict：{payload['verdict']}
candidate_ready：{str(payload['candidate_ready']).lower()}

## Scope

- current_dir: `{payload['current_dir']}`
- candidate_dir: `{payload['candidate_dir']}`

## Transformation

- kind: `{payload['transformation']['kind']}`
- summary: {payload['transformation']['summary']}

## Excluded Pending Items

| approval_id | eco_name | stage_name | approval_deadline | assignee |
|---|---|---|---|---|
{excluded_rows}

## Count Summary

| Metric | current | candidate | Δ |
|---|---:|---:|---:|
| `items_count` | {current['items_count']} | {candidate['items_count']} | {candidate['items_count'] - current['items_count']} |
| `pending_count` | {current['pending_count']} | {candidate['pending_count']} | {candidate['pending_count'] - current['pending_count']} |
| `overdue_count` | {current['overdue_count']} | {candidate['overdue_count']} | {candidate['overdue_count'] - current['overdue_count']} |
| `escalated_count` | {current['escalated_count']} | {candidate['escalated_count']} | {candidate['escalated_count'] - current['escalated_count']} |
| `total_anomalies` | {current['total_anomalies']} | {candidate['total_anomalies']} | {candidate['total_anomalies'] - current['total_anomalies']} |

## Decision

- kind: `{payload['decision']['kind']}`
- summary: {payload['decision']['summary']}

## Candidate Artifacts

- `candidate/summary.json`
- `candidate/items.json`
- `candidate/anomalies.json`
- `candidate/export.json`
- `candidate/export.csv`
- `candidate/OBSERVATION_RESULT.md`
- `candidate/OBSERVATION_EVAL.md`

## Limitations

- `by_role` is intentionally omitted from candidate `summary.json` because the source observation artifacts do not carry a stable role dimension for recomputation.
- This helper does **not** rewrite the tracked baseline. It only produces a stable candidate pack for review.
"""


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            return 0
        return sum(1 for _ in reader)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    current_dir = Path(args.current_dir).resolve()
    parent_dir = current_dir.parent
    candidate_dir = Path(args.output_dir).resolve() if args.output_dir else parent_dir / "candidate"
    output_md = Path(args.output_md).resolve() if args.output_md else parent_dir / "STABLE_READONLY_CANDIDATE.md"
    output_json = Path(args.output_json).resolve() if args.output_json else parent_dir / "stable_readonly_candidate.json"

    summary = load_json(current_dir / "summary.json")
    items = load_json(current_dir / "items.json")
    anomalies = load_json(current_dir / "anomalies.json")
    export_json = load_json(current_dir / "export.json")

    if not isinstance(items, list):
        raise SystemExit("items.json must be a list")
    if not isinstance(export_json, list):
        raise SystemExit("export.json must be a list")

    excluded_pending_items = [
        {
            "approval_id": entry.get("approval_id"),
            "eco_id": entry.get("eco_id"),
            "eco_name": entry.get("eco_name"),
            "stage_id": entry.get("stage_id"),
            "stage_name": entry.get("stage_name"),
            "assignee_id": entry.get("assignee_id"),
            "assignee_username": entry.get("assignee_username"),
            "approval_deadline": entry.get("approval_deadline"),
        }
        for entry in items
        if isinstance(entry, dict) and not entry.get("is_overdue", False)
    ]
    excluded_approval_ids = {str(entry["approval_id"]) for entry in excluded_pending_items if entry.get("approval_id")}
    excluded_eco_ids = {str(entry["eco_id"]) for entry in excluded_pending_items if entry.get("eco_id")}

    candidate_items = [
        entry for entry in items if not (isinstance(entry, dict) and entry.get("approval_id") in excluded_approval_ids)
    ]
    candidate_export_json = [
        entry
        for entry in export_json
        if not (isinstance(entry, dict) and (entry.get("approval_id") in excluded_approval_ids or entry.get("eco_id") in excluded_eco_ids))
    ]
    candidate_anomalies = build_anomalies(anomalies, excluded_approval_ids, excluded_eco_ids)
    candidate_summary = build_summary(candidate_items)

    candidate_dir.mkdir(parents=True, exist_ok=True)
    write_json(candidate_dir / "summary.json", candidate_summary)
    write_json(candidate_dir / "items.json", candidate_items)
    write_json(candidate_dir / "anomalies.json", candidate_anomalies)
    write_json(candidate_dir / "export.json", candidate_export_json)
    write_csv(candidate_dir / "export.csv", candidate_export_json)
    (candidate_dir / "README.txt").write_text(
        "Shared-dev 142 stable readonly candidate artifacts.\n"
        "This candidate excludes future-deadline pending approvals from the current observation set.\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "render_p2_observation_result.py"),
            str(candidate_dir),
            "--operator",
            args.operator,
            "--environment",
            args.environment,
            "--output",
            str(candidate_dir / "OBSERVATION_RESULT.md"),
        ],
        check=True,
        cwd=str(repo_root),
    )
    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "evaluate_p2_observation_results.py"),
            str(candidate_dir),
            "--mode",
            "current-only",
            "--output",
            str(candidate_dir / "OBSERVATION_EVAL.md"),
        ],
        check=True,
        cwd=str(repo_root),
    )

    current_counts = {
        "items_count": len(items),
        "export_json_count": len(export_json),
        "export_csv_rows": count_csv_rows(current_dir / "export.csv"),
        "pending_count": int(summary.get("pending_count", 0)),
        "overdue_count": int(summary.get("overdue_count", 0)),
        "escalated_count": int(summary.get("escalated_count", 0)),
        "total_anomalies": int(anomalies.get("total_anomalies", 0)),
    }
    candidate_counts = {
        "items_count": len(candidate_items),
        "export_json_count": len(candidate_export_json),
        "export_csv_rows": count_csv_rows(candidate_dir / "export.csv"),
        "pending_count": int(candidate_summary.get("pending_count", 0)),
        "overdue_count": int(candidate_summary.get("overdue_count", 0)),
        "escalated_count": int(candidate_summary.get("escalated_count", 0)),
        "total_anomalies": int(candidate_anomalies.get("total_anomalies", 0)),
    }
    candidate_ready = candidate_counts["pending_count"] == 0
    payload = {
        "verdict": "PASS" if candidate_ready else "FAIL",
        "candidate_ready": candidate_ready,
        "current_dir": str(current_dir),
        "candidate_dir": str(candidate_dir),
        "excluded_pending_items": excluded_pending_items,
        "excluded_approval_ids": sorted(excluded_approval_ids),
        "current_counts": current_counts,
        "candidate_counts": candidate_counts,
        "transformation": {
            "kind": "exclude-future-deadline-pending",
            "summary": (
                "No candidate filtering was required."
                if not excluded_pending_items
                else f"Excluded {len(excluded_pending_items)} future-deadline pending approval(s) from the current shared-dev 142 observation set."
            ),
        },
        "decision": {
            "kind": "overdue-only-stable-candidate" if candidate_ready else "candidate-still-unstable",
            "summary": (
                "Candidate contains only overdue approvals, so it no longer ages because of future pending deadlines."
                if candidate_ready
                else "Candidate still contains non-overdue approvals and is not stable yet."
            ),
        },
    }

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_top_markdown(payload), encoding="utf-8")
    write_json(output_json, payload)
    print(output_md)
    print(output_json)


if __name__ == "__main__":
    main()
