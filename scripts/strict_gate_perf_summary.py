#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class MetricSpec:
    rel_json_path: str
    root_key: str
    metric_key: str
    label: str


@dataclass
class MetricRow:
    label: str
    status: str
    p95_ms: str
    threshold_ms: str
    samples: str
    source: str


METRIC_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec(
        rel_json_path="verify-release-orchestration-perf/metrics_summary.json",
        root_key="release_orchestration",
        metric_key="plan",
        label="release_orchestration.plan",
    ),
    MetricSpec(
        rel_json_path="verify-release-orchestration-perf/metrics_summary.json",
        root_key="release_orchestration",
        metric_key="execute_dry_run",
        label="release_orchestration.execute_dry_run",
    ),
    MetricSpec(
        rel_json_path="verify-esign-perf/metrics_summary.json",
        root_key="esign",
        metric_key="sign",
        label="esign.sign",
    ),
    MetricSpec(
        rel_json_path="verify-esign-perf/metrics_summary.json",
        root_key="esign",
        metric_key="verify",
        label="esign.verify",
    ),
    MetricSpec(
        rel_json_path="verify-esign-perf/metrics_summary.json",
        root_key="esign",
        metric_key="audit_summary",
        label="esign.audit_summary",
    ),
    MetricSpec(
        rel_json_path="verify-reports-perf/metrics_summary.json",
        root_key="reports",
        metric_key="search",
        label="reports.search",
    ),
    MetricSpec(
        rel_json_path="verify-reports-perf/metrics_summary.json",
        root_key="reports",
        metric_key="summary",
        label="reports.summary",
    ),
    MetricSpec(
        rel_json_path="verify-reports-perf/metrics_summary.json",
        root_key="reports",
        metric_key="export",
        label="reports.export",
    ),
)


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _fmt_num(value: Any) -> str:
    num = _as_float(value)
    if num is None:
        return "-"
    return f"{num:.3f}"


def _status_from_metric(metric_obj: dict[str, Any]) -> str:
    p95 = _as_float(metric_obj.get("p95_ms"))
    threshold = _as_float(metric_obj.get("threshold_ms"))
    if p95 is None or threshold is None:
        return "UNKNOWN"
    return "PASS" if p95 <= threshold else "FAIL"


def _rel_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _collect_rows(logs_dir: Path) -> List[MetricRow]:
    rows: List[MetricRow] = []

    cache: dict[str, dict[str, Any] | None] = {}
    for spec in METRIC_SPECS:
        json_path = logs_dir / spec.rel_json_path
        payload = cache.get(spec.rel_json_path)
        if spec.rel_json_path not in cache:
            payload = _load_json(json_path)
            cache[spec.rel_json_path] = payload

        if not isinstance(payload, dict):
            continue
        root_obj = payload.get(spec.root_key)
        if not isinstance(root_obj, dict):
            continue
        metric_obj = root_obj.get(spec.metric_key)
        if not isinstance(metric_obj, dict):
            continue

        samples = metric_obj.get("samples")
        rows.append(
            MetricRow(
                label=spec.label,
                status=_status_from_metric(metric_obj),
                p95_ms=_fmt_num(metric_obj.get("p95_ms")),
                threshold_ms=_fmt_num(metric_obj.get("threshold_ms")),
                samples=str(samples) if isinstance(samples, int) else "-",
                source=_rel_to_repo(json_path),
            )
        )

    return rows


def _render_markdown(*, logs_dir: Path, rows: Iterable[MetricRow]) -> str:
    row_list = list(rows)
    lines: List[str] = []
    lines.append("## Perf Smoke Summary")
    lines.append("")
    lines.append(f"- Logs dir: `{_rel_to_repo(logs_dir)}`")
    lines.append("")

    if not row_list:
        lines.append("- No perf metrics found (perf-smokes skipped or failed before metrics output).")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in row_list:
        lines.append(
            f"| {row.label} | {row.status} | {row.p95_ms} | {row.threshold_ms} | {row.samples} | `{row.source}` |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build strict-gate perf-smoke markdown summary")
    parser.add_argument(
        "--logs-dir",
        required=True,
        help="Strict-gate logs directory (for example tmp/strict-gate/STRICT_GATE_CI_<run_id>)",
    )
    parser.add_argument(
        "--out",
        default="-",
        help="Output markdown path. Use '-' for stdout (default).",
    )
    args = parser.parse_args()

    logs_dir = Path(args.logs_dir).resolve()
    rows = _collect_rows(logs_dir)
    markdown = _render_markdown(logs_dir=logs_dir, rows=rows)

    if args.out == "-":
        print(markdown)
    else:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown + "\n", encoding="utf-8")
        print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
