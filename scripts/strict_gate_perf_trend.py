#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]

_TABLE_HEADER = "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |"
_RUN_ID_RE = re.compile(r"^STRICT_GATE_CI_(\d+)$")


@dataclass
class MetricCell:
    metric: str
    status: str
    p95_ms: str
    threshold_ms: str
    samples: str


@dataclass
class TrendRun:
    path: Path
    run_label: str
    metrics: Dict[str, MetricCell]
    has_metrics: bool
    sort_key: tuple[int, int]

    @property
    def overall(self) -> str:
        if not self.has_metrics:
            return "NO_METRICS"
        statuses = {m.status for m in self.metrics.values()}
        if "FAIL" in statuses:
            return "FAIL"
        if "PASS" in statuses:
            return "PASS"
        return "UNKNOWN"


def _rel_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _metric_cell(run: TrendRun, metric_key: str) -> str:
    metric = run.metrics.get(metric_key)
    if not metric:
        return "-"
    p95 = metric.p95_ms.strip() if metric.p95_ms else "-"
    threshold = metric.threshold_ms.strip() if metric.threshold_ms else "-"
    if p95 != "-" and threshold != "-":
        return f"{metric.status} {p95}/{threshold}"
    if p95 != "-":
        return f"{metric.status} {p95}"
    return metric.status


def _parse_run_label(path: Path) -> str:
    stem = path.stem
    if stem.endswith("_PERF"):
        return stem[: -len("_PERF")]
    return stem


def _sort_key(path: Path, run_label: str) -> tuple[int, int]:
    # Prefer CI run_id ordering when present; otherwise use mtime.
    m = _RUN_ID_RE.match(run_label)
    if m:
        return (1, int(m.group(1)))
    try:
        return (0, int(path.stat().st_mtime))
    except OSError:
        return (0, 0)


def _parse_perf_summary(path: Path) -> Optional[TrendRun]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    metrics: Dict[str, MetricCell] = {}
    in_table = False

    for line in lines:
        if line.strip() == _TABLE_HEADER:
            in_table = True
            continue

        if not in_table:
            continue

        if not line.strip().startswith("|"):
            break
        if line.strip().startswith("| ---"):
            continue

        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 6:
            continue

        metric, status, p95_ms, threshold_ms, samples, _source = cols[:6]
        if not metric:
            continue
        metrics[metric] = MetricCell(
            metric=metric,
            status=status or "UNKNOWN",
            p95_ms=p95_ms or "-",
            threshold_ms=threshold_ms or "-",
            samples=samples or "-",
        )

    run_label = _parse_run_label(path)
    has_metrics = len(metrics) > 0
    return TrendRun(
        path=path,
        run_label=run_label,
        metrics=metrics,
        has_metrics=has_metrics,
        sort_key=_sort_key(path, run_label),
    )


def _discover_runs(report_dir: Path, *, glob: str, include_empty: bool) -> List[TrendRun]:
    runs: List[TrendRun] = []
    for path in sorted(report_dir.glob(glob)):
        if path.name.endswith("_PERF_TREND.md"):
            continue
        parsed = _parse_perf_summary(path)
        if parsed is None:
            continue
        if (not include_empty) and (not parsed.has_metrics):
            continue
        runs.append(parsed)

    runs.sort(key=lambda r: r.sort_key, reverse=True)
    return runs


def _write_trend(out_path: Path, *, runs: List[TrendRun], report_dir: Path, limit: int, include_empty: bool) -> None:
    metric_order = [
        "release_orchestration.plan",
        "release_orchestration.execute_dry_run",
        "esign.sign",
        "esign.verify",
        "esign.audit_summary",
        "reports.search",
        "reports.summary",
        "reports.export",
    ]

    now = datetime.now().isoformat(timespec="seconds")
    lines: List[str] = []
    lines.append("# Strict Gate Perf Smoke Trend")
    lines.append("")
    lines.append(f"- Generated: `{now}`")
    lines.append(f"- Source dir: `{_rel_to_repo(report_dir)}`")
    lines.append(f"- Include empty runs: `{'true' if include_empty else 'false'}`")
    lines.append(f"- Runs discovered: `{len(runs)}` (showing latest `{min(limit, len(runs))}`)")
    lines.append("")
    lines.append("## Latest Runs")
    lines.append("")

    if not runs:
        lines.append("- No perf summary runs found.")
        lines.append("")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    headers = [
        "Run",
        "Overall",
        "Perf Report",
        "rel-orch.plan",
        "rel-orch.execute",
        "esign.sign",
        "esign.verify",
        "esign.audit",
        "reports.search",
        "reports.summary",
        "reports.export",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for run in runs[:limit]:
        row = [
            f"`{run.run_label}`",
            run.overall,
            f"`{_rel_to_repo(run.path)}`",
            _metric_cell(run, metric_order[0]),
            _metric_cell(run, metric_order[1]),
            _metric_cell(run, metric_order[2]),
            _metric_cell(run, metric_order[3]),
            _metric_cell(run, metric_order[4]),
            _metric_cell(run, metric_order[5]),
            _metric_cell(run, metric_order[6]),
            _metric_cell(run, metric_order[7]),
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Metric cells show `STATUS p95/threshold` in milliseconds.")
    lines.append("- `NO_METRICS` means the run had no perf metric table (for example perf-smokes were skipped).")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate strict-gate perf trend from *_PERF.md summaries")
    parser.add_argument(
        "--dir",
        default=str(REPO_ROOT / "docs" / "DAILY_REPORTS"),
        help="Directory containing STRICT_GATE_*_PERF.md files",
    )
    parser.add_argument(
        "--glob",
        default="STRICT_GATE_*_PERF.md",
        help="Glob pattern for perf summaries inside --dir",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "docs" / "DAILY_REPORTS" / "STRICT_GATE_PERF_TREND.md"),
        help="Output markdown path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Max number of runs to include",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Include runs without metric tables (NO_METRICS)",
    )
    args = parser.parse_args()

    report_dir = Path(args.dir).resolve()
    out_path = Path(args.out).resolve()
    limit = max(1, int(args.limit))

    runs = _discover_runs(report_dir, glob=args.glob, include_empty=args.include_empty)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_trend(out_path, runs=runs, report_dir=report_dir, limit=limit, include_empty=bool(args.include_empty))
    print(f"Trend: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
