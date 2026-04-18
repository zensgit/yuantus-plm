#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path


SUMMARY_KEYS = ("pending_count", "overdue_count", "escalated_count")
COUNT_KEYS = ("items_count", "export_json_count", "export_csv_rows")
ANOMALY_KEYS = (
    "total_anomalies",
    "no_candidates",
    "escalated_unresolved",
    "overdue_not_escalated",
)
METRIC_KEYS = SUMMARY_KEYS + COUNT_KEYS + ANOMALY_KEYS


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"Error reading {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error parsing JSON {path}: {exc}") from exc


def count_csv_rows(path: Path):
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if header is None:
                return 0
            return sum(1 for _ in reader)
    except OSError as exc:
        raise SystemExit(f"Error reading CSV {path}: {exc}") from exc


def build_snapshot(result_dir: Path):
    summary = load_json(result_dir / "summary.json")
    items = load_json(result_dir / "items.json")
    anomalies = load_json(result_dir / "anomalies.json")
    export_json = load_json(result_dir / "export.json")
    export_csv_rows = count_csv_rows(result_dir / "export.csv")

    derived = {
        "pending_count": sum(1 for item in items if not item.get("is_overdue")),
        "overdue_count": sum(1 for item in items if item.get("is_overdue")),
        "escalated_count": sum(1 for item in items if item.get("is_escalated")),
    }
    anomaly_counts = {
        "total_anomalies": int(anomalies.get("total_anomalies", 0)),
        "no_candidates": len(anomalies.get("no_candidates", [])),
        "escalated_unresolved": len(anomalies.get("escalated_unresolved", [])),
        "overdue_not_escalated": len(anomalies.get("overdue_not_escalated", [])),
    }

    return {
        "result_dir": result_dir,
        "summary": {key: int(summary.get(key, 0)) for key in SUMMARY_KEYS},
        "counts": {
            "items_count": len(items),
            "export_json_count": len(export_json),
            "export_csv_rows": export_csv_rows,
        },
        "anomalies": anomaly_counts,
        "derived": derived,
    }


def flatten_metrics(snapshot):
    flat = {}
    for section in ("summary", "counts", "anomalies"):
        flat.update(snapshot[section])
    return flat


def evaluate_snapshot(label: str, snapshot):
    flat = flatten_metrics(snapshot)
    checks = []

    count_values = [flat["items_count"], flat["export_json_count"], flat["export_csv_rows"]]
    checks.append(
        {
            "scope": label,
            "name": "items/export row count consistency",
            "ok": len(set(count_values)) == 1,
            "detail": (
                f"items_count={flat['items_count']}, "
                f"export_json_count={flat['export_json_count']}, "
                f"export_csv_rows={flat['export_csv_rows']}"
            ),
        }
    )

    for key in SUMMARY_KEYS:
        checks.append(
            {
                "scope": label,
                "name": f"summary matches items for {key}",
                "ok": snapshot["summary"][key] == snapshot["derived"][key],
                "detail": f"summary={snapshot['summary'][key]}, derived={snapshot['derived'][key]}",
            }
        )

    derived_total_anomalies = (
        snapshot["anomalies"]["no_candidates"]
        + snapshot["anomalies"]["escalated_unresolved"]
        + snapshot["anomalies"]["overdue_not_escalated"]
    )
    checks.append(
        {
            "scope": label,
            "name": "anomaly total matches category counts",
            "ok": snapshot["anomalies"]["total_anomalies"] == derived_total_anomalies,
            "detail": (
                f"total_anomalies={snapshot['anomalies']['total_anomalies']}, "
                f"derived_total={derived_total_anomalies}"
            ),
        }
    )

    return checks


def parse_expected_deltas(raw_values):
    expected = {}
    for raw in raw_values:
        if "=" not in raw:
            raise SystemExit(f"Invalid --expect-delta '{raw}'; expected <metric>=<signed-int>")
        metric, raw_delta = raw.split("=", 1)
        metric = metric.strip()
        raw_delta = raw_delta.strip()
        if metric not in METRIC_KEYS:
            raise SystemExit(
                f"Invalid --expect-delta metric '{metric}'; expected one of: {', '.join(METRIC_KEYS)}"
            )
        try:
            expected[metric] = int(raw_delta)
        except ValueError as exc:
            raise SystemExit(
                f"Invalid --expect-delta value '{raw_delta}' for metric '{metric}'; expected signed int"
            ) from exc
    return expected


def evaluate_readonly(baseline, current):
    checks = []
    baseline_flat = flatten_metrics(baseline)
    current_flat = flatten_metrics(current)

    for key in METRIC_KEYS:
        left = baseline_flat[key]
        right = current_flat[key]
        checks.append(
            {
                "scope": "comparison",
                "name": f"readonly stability for {key}",
                "ok": left == right,
                "detail": f"baseline={left}, current={right}, delta={right - left}",
            }
        )

    return checks


def evaluate_state_change(baseline, current, expected_deltas):
    checks = []
    baseline_flat = flatten_metrics(baseline)
    current_flat = flatten_metrics(current)

    for key, expected_delta in expected_deltas.items():
        left = baseline_flat[key]
        right = current_flat[key]
        actual_delta = right - left
        checks.append(
            {
                "scope": "comparison",
                "name": f"state-change delta for {key}",
                "ok": actual_delta == expected_delta,
                "detail": (
                    f"baseline={left}, current={right}, "
                    f"actual_delta={actual_delta}, expected_delta={expected_delta}"
                ),
            }
        )

    return checks


def render_markdown(mode: str, current, checks, baseline=None):
    overall_ok = all(check["ok"] for check in checks)
    lines = [
        "# P2 Observation Evaluation",
        "",
        f"- mode: `{mode}`",
        f"- current: `{current['result_dir']}`",
    ]
    if baseline is not None:
        lines.append(f"- baseline: `{baseline['result_dir']}`")
    lines.extend(
        [
            "",
            "## Overall",
            "",
            f"- verdict: {'PASS' if overall_ok else 'FAIL'}",
            f"- checks: {sum(1 for check in checks if check['ok'])}/{len(checks)} passed",
            "",
            "## Check Results",
            "",
            "| Scope | Check | Status | Detail |",
            "|---|---|---|---|",
        ]
    )
    for check in checks:
        lines.append(
            f"| `{check['scope']}` | {check['name']} | {'PASS' if check['ok'] else 'FAIL'} | {check['detail']} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate P2 observation artifacts for consistency and expected regression behavior."
    )
    parser.add_argument("current_dir", help="Current observation result directory")
    parser.add_argument(
        "--mode",
        choices=("current-only", "readonly", "state-change"),
        default="current-only",
        help="Evaluation mode",
    )
    parser.add_argument("--baseline-dir", help="Baseline observation result directory")
    parser.add_argument(
        "--expect-delta",
        action="append",
        default=[],
        help="Expected metric delta for state-change mode, for example overdue_count=1",
    )
    parser.add_argument(
        "--output",
        help="Output markdown path. Default: <current_dir>/OBSERVATION_EVAL.md",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    current_dir = Path(args.current_dir).resolve()
    baseline_dir = Path(args.baseline_dir).resolve() if args.baseline_dir else None
    output_path = Path(args.output).resolve() if args.output else current_dir / "OBSERVATION_EVAL.md"

    required = ("summary.json", "items.json", "anomalies.json", "export.json", "export.csv")
    directories = [current_dir]
    if baseline_dir is not None:
        directories.append(baseline_dir)
    for directory in directories:
        for filename in required:
            path = directory / filename
            if not path.is_file():
                raise SystemExit(f"Missing required artifact: {path}")

    if args.mode in {"readonly", "state-change"} and baseline_dir is None:
        raise SystemExit(f"--mode {args.mode} requires --baseline-dir")
    if args.mode == "current-only" and args.expect_delta:
        raise SystemExit("--expect-delta is only valid with --mode state-change")

    expected_deltas = parse_expected_deltas(args.expect_delta)
    if args.mode == "state-change" and not expected_deltas:
        raise SystemExit("--mode state-change requires at least one --expect-delta")
    if args.mode != "state-change" and expected_deltas:
        raise SystemExit("--expect-delta is only valid with --mode state-change")

    current = build_snapshot(current_dir)
    baseline = build_snapshot(baseline_dir) if baseline_dir is not None else None

    checks = evaluate_snapshot("current", current)
    if baseline is not None:
        checks.extend(evaluate_snapshot("baseline", baseline))
    if args.mode == "readonly":
        checks.extend(evaluate_readonly(baseline, current))
    elif args.mode == "state-change":
        checks.extend(evaluate_state_change(baseline, current, expected_deltas))

    markdown = render_markdown(args.mode, current, checks, baseline=baseline)
    output_path.write_text(markdown, encoding="utf-8")
    print(output_path)
    raise SystemExit(0 if all(check["ok"] for check in checks) else 1)


if __name__ == "__main__":
    main()
