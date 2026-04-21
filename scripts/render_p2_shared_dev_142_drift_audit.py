#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Error reading artifact {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing JSON artifact {path}: {exc}") from exc


def count_csv_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
    except OSError as exc:
        raise SystemExit(f"Error reading CSV artifact {path}: {exc}") from exc
    if not rows:
        return 0
    return max(len(rows) - 1, 0)


def collect_metrics(result_dir: Path) -> tuple[dict, dict]:
    summary_path = result_dir / "summary.json"
    items_path = result_dir / "items.json"
    anomalies_path = result_dir / "anomalies.json"
    export_json_path = result_dir / "export.json"
    export_csv_path = result_dir / "export.csv"

    for path in (summary_path, items_path, anomalies_path, export_json_path, export_csv_path):
        if not path.is_file():
            raise SystemExit(f"Missing required artifact: {path}")

    summary = load_json(summary_path)
    items = load_json(items_path)
    anomalies = load_json(anomalies_path)
    export_json = load_json(export_json_path)

    if not isinstance(summary, dict):
        raise SystemExit(f"summary.json must parse as object: {summary_path}")
    if not isinstance(items, list):
        raise SystemExit(f"items.json must parse as array: {items_path}")
    if not isinstance(anomalies, dict):
        raise SystemExit(f"anomalies.json must parse as object: {anomalies_path}")
    if not isinstance(export_json, list):
        raise SystemExit(f"export.json must parse as array: {export_json_path}")

    metrics = {
        "pending_count": int(summary.get("pending_count", 0)),
        "overdue_count": int(summary.get("overdue_count", 0)),
        "escalated_count": int(summary.get("escalated_count", 0)),
        "items_count": len(items),
        "export_json_count": len(export_json),
        "export_csv_rows": count_csv_rows(export_csv_path),
        "total_anomalies": int(anomalies.get("total_anomalies", 0)),
        "no_candidates": len(anomalies.get("no_candidates", [])),
        "escalated_unresolved": len(anomalies.get("escalated_unresolved", [])),
        "overdue_not_escalated": len(anomalies.get("overdue_not_escalated", [])),
    }

    approval_ids = sorted(
        str(item["approval_id"])
        for item in items
        if isinstance(item, dict) and item.get("approval_id") is not None
    )

    details = {
        "summary": summary,
        "items": items,
        "anomalies": anomalies,
        "approval_ids": approval_ids,
    }
    return metrics, details


def compute_changed_metrics(baseline_metrics: dict, current_metrics: dict) -> list[dict]:
    changed: list[dict] = []
    for key in (
        "pending_count",
        "overdue_count",
        "escalated_count",
        "items_count",
        "export_json_count",
        "export_csv_rows",
        "total_anomalies",
        "no_candidates",
        "escalated_unresolved",
        "overdue_not_escalated",
    ):
        baseline_value = baseline_metrics.get(key, 0)
        current_value = current_metrics.get(key, 0)
        if baseline_value != current_value:
            changed.append(
                {
                    "metric": key,
                    "baseline": baseline_value,
                    "current": current_value,
                    "delta": current_value - baseline_value,
                }
            )
    return changed


def render_markdown(
    baseline_dir: Path,
    current_dir: Path,
    baseline_label: str,
    current_label: str,
    baseline_metrics: dict,
    current_metrics: dict,
    changed_metrics: list[dict],
    added_ids: list[str],
    removed_ids: list[str],
) -> str:
    verdict = "PASS" if not changed_metrics and not added_ids and not removed_ids else "FAIL"
    changed_lines = "\n".join(
        f"| `{entry['metric']}` | `{entry['baseline']}` | `{entry['current']}` | `{entry['delta']}` |"
        for entry in changed_metrics
    )
    if not changed_lines:
        changed_lines = "| _(none)_ | `-` | `-` | `0` |"

    def _fmt_ids(values: list[str]) -> str:
        if not values:
            return "- _(none)_"
        return "\n".join(f"- `{value}`" for value in values)

    return f"""# Shared-dev 142 Drift Audit

日期：{date.today().isoformat()}
verdict：{verdict}

## Scope

- baseline_label: `{baseline_label}`
- current_label: `{current_label}`
- baseline_dir: `{baseline_dir}`
- current_dir: `{current_dir}`

## Key Metrics

| metric | {baseline_label} | {current_label} | delta |
|---|---:|---:|---:|
{changed_lines}

## Full Metric Snapshot

### {baseline_label}

```json
{json.dumps(baseline_metrics, ensure_ascii=False, indent=2)}
```

### {current_label}

```json
{json.dumps(current_metrics, ensure_ascii=False, indent=2)}
```

## Approval ID Diff

### Added in {current_label}
{_fmt_ids(added_ids)}

### Removed from {baseline_label}
{_fmt_ids(removed_ids)}

## Next

- if `verdict=PASS`, the current readonly surface still matches the frozen baseline
- if `verdict=FAIL` but the deltas are expected state changes, use the readonly refreeze flow
- if `verdict=FAIL` and the deltas are unexpected, investigate the shared-dev 142 write history before any refreeze
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a shared-dev 142 drift audit from a baseline result dir and a current result dir."
    )
    parser.add_argument("baseline_dir", help="Baseline observation result directory")
    parser.add_argument("current_dir", help="Current observation result directory")
    parser.add_argument(
        "--baseline-label",
        default="shared-dev-142-readonly-20260421",
        help="Label used for the baseline column",
    )
    parser.add_argument(
        "--current-label",
        default="current-drift-audit",
        help="Label used for the current column",
    )
    parser.add_argument(
        "--output-md",
        help="Output markdown path. Default: <current_dir>/DRIFT_AUDIT.md",
    )
    parser.add_argument(
        "--output-json",
        help="Output JSON path. Default: <current_dir>/drift_audit.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    baseline_dir = Path(args.baseline_dir).resolve()
    current_dir = Path(args.current_dir).resolve()

    baseline_metrics, baseline_details = collect_metrics(baseline_dir)
    current_metrics, current_details = collect_metrics(current_dir)

    baseline_ids = set(baseline_details["approval_ids"])
    current_ids = set(current_details["approval_ids"])
    added_ids = sorted(current_ids - baseline_ids)
    removed_ids = sorted(baseline_ids - current_ids)
    changed_metrics = compute_changed_metrics(baseline_metrics, current_metrics)
    verdict = "PASS" if not changed_metrics and not added_ids and not removed_ids else "FAIL"

    output_md = (
        Path(args.output_md).resolve()
        if args.output_md
        else current_dir / "DRIFT_AUDIT.md"
    )
    output_json = (
        Path(args.output_json).resolve()
        if args.output_json
        else current_dir / "drift_audit.json"
    )

    payload = {
        "verdict": verdict,
        "baseline_label": args.baseline_label,
        "current_label": args.current_label,
        "baseline_dir": str(baseline_dir),
        "current_dir": str(current_dir),
        "baseline_metrics": baseline_metrics,
        "current_metrics": current_metrics,
        "changed_metrics": changed_metrics,
        "added_approval_ids": added_ids,
        "removed_approval_ids": removed_ids,
    }

    output_md.write_text(
        render_markdown(
            baseline_dir=baseline_dir,
            current_dir=current_dir,
            baseline_label=args.baseline_label,
            current_label=args.current_label,
            baseline_metrics=baseline_metrics,
            current_metrics=current_metrics,
            changed_metrics=changed_metrics,
            added_ids=added_ids,
            removed_ids=removed_ids,
        ),
        encoding="utf-8",
    )
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_md)


if __name__ == "__main__":
    main()
