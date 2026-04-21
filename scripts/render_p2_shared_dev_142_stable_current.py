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
        description=(
            "Render an effective stable current pack for shared-dev 142 readonly "
            "checks by excluding pending approvals from the raw current observation set."
        )
    )
    parser.add_argument("current_dir", help="Raw current observation result dir")
    parser.add_argument("--output-dir", help="Output effective-current dir. Default: <current_dir>/..")
    parser.add_argument(
        "--output-md",
        help="Output markdown path. Default: <output_dir>/STABLE_CURRENT_TRANSFORM.md",
    )
    parser.add_argument(
        "--output-json",
        help="Output JSON path. Default: <output_dir>/stable_current_transform.json",
    )
    parser.add_argument(
        "--environment",
        default="shared-dev-142-stable-current",
        help="Environment label for nested OBSERVATION_RESULT.md",
    )
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
    stable = {
        "no_candidates": filter_entries(anomalies.get("no_candidates", []), excluded_approval_ids, excluded_eco_ids),
        "escalated_unresolved": filter_entries(anomalies.get("escalated_unresolved", []), excluded_approval_ids, excluded_eco_ids),
        "overdue_not_escalated": filter_entries(anomalies.get("overdue_not_escalated", []), excluded_approval_ids, excluded_eco_ids),
    }
    stable["total_anomalies"] = (
        len(stable["no_candidates"])
        + len(stable["escalated_unresolved"])
        + len(stable["overdue_not_escalated"])
    )
    return stable


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


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            return 0
        return sum(1 for _ in reader)


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

    raw_counts = payload["raw_counts"]
    stable_counts = payload["stable_counts"]

    return f"""# Shared-dev 142 Stable Current Transform

日期：{date.today().isoformat()}
verdict：{payload['verdict']}
stable_current_ready：{str(payload['stable_current_ready']).lower()}

## Scope

- raw_current_dir: `{payload['raw_current_dir']}`
- stable_current_dir: `{payload['stable_current_dir']}`

## Policy

- kind: `{payload['policy']['kind']}`
- summary: {payload['policy']['summary']}

## Excluded Pending Items

| approval_id | eco_name | stage_name | approval_deadline | assignee |
|---|---|---|---|---|
{excluded_rows}

## Count Summary

| Metric | raw current | stable current | Δ |
|---|---:|---:|---:|
| `items_count` | {raw_counts['items_count']} | {stable_counts['items_count']} | {stable_counts['items_count'] - raw_counts['items_count']} |
| `pending_count` | {raw_counts['pending_count']} | {stable_counts['pending_count']} | {stable_counts['pending_count'] - raw_counts['pending_count']} |
| `overdue_count` | {raw_counts['overdue_count']} | {stable_counts['overdue_count']} | {stable_counts['overdue_count'] - raw_counts['overdue_count']} |
| `escalated_count` | {raw_counts['escalated_count']} | {stable_counts['escalated_count']} | {stable_counts['escalated_count'] - raw_counts['escalated_count']} |
| `total_anomalies` | {raw_counts['total_anomalies']} | {stable_counts['total_anomalies']} | {stable_counts['total_anomalies'] - raw_counts['total_anomalies']} |

## Decision

- kind: `{payload['decision']['kind']}`
- summary: {payload['decision']['summary']}

## Stable Current Artifacts

- `summary.json`
- `items.json`
- `anomalies.json`
- `export.json`
- `export.csv`
- `OBSERVATION_RESULT.md`
- `OBSERVATION_EVAL.md`
- `README.txt`
"""


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    raw_current_dir = Path(args.current_dir).resolve()
    stable_current_dir = Path(args.output_dir).resolve() if args.output_dir else raw_current_dir.parent
    output_md = Path(args.output_md).resolve() if args.output_md else stable_current_dir / "STABLE_CURRENT_TRANSFORM.md"
    output_json = (
        Path(args.output_json).resolve() if args.output_json else stable_current_dir / "stable_current_transform.json"
    )

    summary = load_json(raw_current_dir / "summary.json")
    items = load_json(raw_current_dir / "items.json")
    anomalies = load_json(raw_current_dir / "anomalies.json")
    export_json = load_json(raw_current_dir / "export.json")

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

    stable_items = [
        entry for entry in items if not (isinstance(entry, dict) and entry.get("approval_id") in excluded_approval_ids)
    ]
    stable_export_json = [
        entry
        for entry in export_json
        if not (
            isinstance(entry, dict)
            and (entry.get("approval_id") in excluded_approval_ids or entry.get("eco_id") in excluded_eco_ids)
        )
    ]
    stable_anomalies = build_anomalies(anomalies, excluded_approval_ids, excluded_eco_ids)
    stable_summary = build_summary(stable_items)

    stable_current_dir.mkdir(parents=True, exist_ok=True)
    write_json(stable_current_dir / "summary.json", stable_summary)
    write_json(stable_current_dir / "items.json", stable_items)
    write_json(stable_current_dir / "anomalies.json", stable_anomalies)
    write_json(stable_current_dir / "export.json", stable_export_json)
    write_csv(stable_current_dir / "export.csv", stable_export_json)
    (stable_current_dir / "README.txt").write_text(
        "Shared-dev 142 stable current artifacts.\n"
        "This effective current excludes pending approvals so the official overdue-only readonly baseline stays stable.\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "render_p2_observation_result.py"),
            str(stable_current_dir),
            "--operator",
            args.operator,
            "--environment",
            args.environment,
            "--output",
            str(stable_current_dir / "OBSERVATION_RESULT.md"),
        ],
        check=True,
        cwd=str(repo_root),
    )
    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "evaluate_p2_observation_results.py"),
            str(stable_current_dir),
            "--mode",
            "current-only",
            "--output",
            str(stable_current_dir / "OBSERVATION_EVAL.md"),
        ],
        check=True,
        cwd=str(repo_root),
    )

    raw_counts = {
        "items_count": len(items),
        "export_json_count": len(export_json),
        "export_csv_rows": count_csv_rows(raw_current_dir / "export.csv"),
        "pending_count": int(summary.get("pending_count", 0)),
        "overdue_count": int(summary.get("overdue_count", 0)),
        "escalated_count": int(summary.get("escalated_count", 0)),
        "total_anomalies": int(anomalies.get("total_anomalies", 0)),
    }
    stable_counts = {
        "items_count": len(stable_items),
        "export_json_count": len(stable_export_json),
        "export_csv_rows": count_csv_rows(stable_current_dir / "export.csv"),
        "pending_count": int(stable_summary.get("pending_count", 0)),
        "overdue_count": int(stable_summary.get("overdue_count", 0)),
        "escalated_count": int(stable_summary.get("escalated_count", 0)),
        "total_anomalies": int(stable_anomalies.get("total_anomalies", 0)),
    }

    payload = {
        "verdict": "PASS",
        "stable_current_ready": True,
        "raw_current_dir": str(raw_current_dir),
        "stable_current_dir": str(stable_current_dir),
        "excluded_pending_items": excluded_pending_items,
        "excluded_approval_ids": sorted(excluded_approval_ids),
        "raw_counts": raw_counts,
        "stable_counts": stable_counts,
        "policy": {
            "kind": "overdue-only-stable",
            "summary": (
                "No pending approvals were excluded."
                if not excluded_pending_items
                else f"Excluded {len(excluded_pending_items)} pending approval(s) from the raw shared-dev 142 observation set."
            ),
        },
        "decision": {
            "kind": "overdue-only-stable-current",
            "summary": "Effective current now matches the overdue-only readonly compare policy.",
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
