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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render shared-dev 142 readonly refreeze readiness from a current observation result directory."
    )
    parser.add_argument("current_dir", help="Current observation result dir containing summary/items/anomalies JSON")
    parser.add_argument("--output-md", help="Output markdown path. Default: <current_dir>/REFREEZE_READINESS.md")
    parser.add_argument("--output-json", help="Output JSON path. Default: <current_dir>/refreeze_readiness.json")
    return parser.parse_args()


def render_markdown(payload: dict) -> str:
    pending_rows = "\n".join(
        (
            f"| `{entry['approval_id']}` | `{entry['eco_name']}` | `{entry['stage_name']}` | "
            f"`{entry['approval_deadline']}` | `{entry['assignee_username']}` |"
        )
        for entry in payload["future_deadline_pending_items"]
    )
    if not pending_rows:
        pending_rows = "| _(none)_ | `-` | `-` | `-` | `-` |"

    return f"""# Shared-dev 142 Readonly Refreeze Readiness

日期：{date.today().isoformat()}
verdict：{payload['verdict']}
ready：{str(payload['ready']).lower()}

## Scope

- current_dir: `{payload['current_dir']}`

## Summary

- pending_count: `{payload['summary'].get('pending_count')}`
- overdue_count: `{payload['summary'].get('overdue_count')}`
- escalated_count: `{payload['summary'].get('escalated_count')}`
- total_anomalies: `{payload['anomalies'].get('total_anomalies')}`

## Future-deadline Pending Items

| approval_id | eco_name | stage_name | approval_deadline | assignee |
|---|---|---|---|---|
{pending_rows}

## Decision

- kind: `{payload['decision']['kind']}`
- summary: {payload['decision']['summary']}

## Next

- if `ready=true`, this current result can be promoted as the next tracked readonly baseline
- if `ready=false`, do **not** refreeze yet; either wait for the pending deadline to pass or redesign the readonly baseline so it excludes time-sensitive items
"""


def main() -> None:
    args = parse_args()
    current_dir = Path(args.current_dir).resolve()
    items = load_json(current_dir / "items.json")
    summary = load_json(current_dir / "summary.json")
    anomalies = load_json(current_dir / "anomalies.json")

    if not isinstance(items, list):
        raise SystemExit("items.json must be a list")

    future_deadline_pending_items = [
        {
            "approval_id": entry.get("approval_id"),
            "eco_id": entry.get("eco_id"),
            "eco_name": entry.get("eco_name"),
            "stage_id": entry.get("stage_id"),
            "stage_name": entry.get("stage_name"),
            "assignee_username": entry.get("assignee_username"),
            "approval_deadline": entry.get("approval_deadline"),
        }
        for entry in items
        if isinstance(entry, dict) and not entry.get("is_overdue", False)
    ]

    ready = not future_deadline_pending_items
    decision = {
        "kind": "stable-readonly" if ready else "future-deadline-pending",
        "summary": (
            "No future-deadline pending approvals remain in the current shared-dev 142 observation set."
            if ready
            else f"{len(future_deadline_pending_items)} pending approval(s) still have future deadlines, so a readonly refreeze would age out again."
        ),
    }

    payload = {
        "ready": ready,
        "verdict": "PASS" if ready else "FAIL",
        "current_dir": str(current_dir),
        "summary": summary,
        "anomalies": anomalies,
        "future_deadline_pending_items": future_deadline_pending_items,
        "decision": decision,
    }

    output_md = Path(args.output_md).resolve() if args.output_md else current_dir / "REFREEZE_READINESS.md"
    output_json = Path(args.output_json).resolve() if args.output_json else current_dir / "refreeze_readiness.json"
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_md)
    print(output_json)


if __name__ == "__main__":
    main()
