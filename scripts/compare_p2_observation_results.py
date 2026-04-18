#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path


CORE_SUMMARY_KEYS = ("pending_count", "overdue_count", "escalated_count")
CORE_ANOMALY_KEYS = (
    "total_anomalies",
    "no_candidates",
    "escalated_unresolved",
    "overdue_not_escalated",
)


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

    snapshot = {
        "summary": {key: int(summary.get(key, 0)) for key in CORE_SUMMARY_KEYS},
        "counts": {
            "items_count": len(items),
            "export_json_count": len(export_json),
            "export_csv_rows": export_csv_rows,
        },
        "anomalies": {key: int(anomalies.get(key, 0) if key == "total_anomalies" else len(anomalies.get(key, []))) for key in CORE_ANOMALY_KEYS},
    }
    return snapshot


def render_table(section_name: str, left_label: str, right_label: str, values: dict, extractor):
    lines = [f"## {section_name}", "", f"| Metric | {left_label} | {right_label} | Δ |", "|---|---:|---:|---:|"]
    for key, left_value, right_value in extractor(values):
        lines.append(f"| `{key}` | {left_value} | {right_value} | {right_value - left_value} |")
    lines.append("")
    return "\n".join(lines)


def iter_section_pairs(section_values):
    for key in section_values["left"]:
        yield key, section_values["left"][key], section_values["right"][key]


def render_markdown(baseline_dir: Path, current_dir: Path, baseline_label: str, current_label: str, baseline, current):
    summary_values = {"left": baseline["summary"], "right": current["summary"]}
    count_values = {"left": baseline["counts"], "right": current["counts"]}
    anomaly_values = {"left": baseline["anomalies"], "right": current["anomalies"]}

    lines = [
        "# P2 Observation Result Diff",
        "",
        f"- baseline: `{baseline_dir}`",
        f"- current: `{current_dir}`",
        "",
        render_table("Summary", baseline_label, current_label, summary_values, iter_section_pairs),
        render_table("Counts", baseline_label, current_label, count_values, iter_section_pairs),
        render_table("Anomalies", baseline_label, current_label, anomaly_values, iter_section_pairs),
        "## Consistency Checks",
        "",
        f"- `{baseline_label}`: items/export-json/export-csv {'一致' if len({baseline['counts']['items_count'], baseline['counts']['export_json_count'], baseline['counts']['export_csv_rows']}) == 1 else '不一致'}",
        f"- `{current_label}`: items/export-json/export-csv {'一致' if len({current['counts']['items_count'], current['counts']['export_json_count'], current['counts']['export_csv_rows']}) == 1 else '不一致'}",
        "",
        "## Interpretation Stub",
        "",
        "- 如果这是只读回归，预期主要指标应保持稳定。",
        "- 如果这是状态变更回归，差异必须能被 runbook 或实验目标解释。",
        "",
    ]
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Compare two P2 observation result directories and render a Markdown diff.")
    parser.add_argument("baseline_dir", help="Baseline observation result directory")
    parser.add_argument("current_dir", help="Current observation result directory")
    parser.add_argument("--baseline-label", default="baseline", help="Label for the baseline column")
    parser.add_argument("--current-label", default="current", help="Label for the current column")
    parser.add_argument("--output", help="Output markdown path. Default: <current_dir>/OBSERVATION_DIFF.md")
    return parser.parse_args()


def main():
    args = parse_args()
    baseline_dir = Path(args.baseline_dir).resolve()
    current_dir = Path(args.current_dir).resolve()
    output_path = Path(args.output).resolve() if args.output else current_dir / "OBSERVATION_DIFF.md"

    required = ("summary.json", "items.json", "anomalies.json", "export.json", "export.csv")
    for directory in (baseline_dir, current_dir):
        for filename in required:
            path = directory / filename
            if not path.is_file():
                raise SystemExit(f"Missing required artifact: {path}")

    baseline = build_snapshot(baseline_dir)
    current = build_snapshot(current_dir)
    markdown = render_markdown(
        baseline_dir,
        current_dir,
        args.baseline_label,
        args.current_label,
        baseline,
        current,
    )
    output_path.write_text(markdown, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
