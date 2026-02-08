#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class ScenarioRow:
    name: str
    measured: str
    status: str


@dataclass
class PerfRun:
    path: Path
    started: str
    git: str
    scenarios: Dict[str, ScenarioRow]

    @property
    def overall(self) -> str:
        statuses = {row.status for row in self.scenarios.values()}
        if "FAIL" in statuses:
            return "FAIL"
        # Treat SKIP as non-failing for trend purposes.
        return "PASS"


_STARTED_RE = re.compile(r"^- Started: `([^`]+)`\s*$")
_GIT_RE = re.compile(r"^- Git: `([^`]+)`\s*$")


def _parse_report(path: Path) -> Optional[PerfRun]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    started = ""
    git = ""

    in_table = False
    scenarios: Dict[str, ScenarioRow] = {}
    for line in lines:
        if not started:
            m = _STARTED_RE.match(line)
            if m:
                started = m.group(1).strip()
                continue
        if not git:
            m = _GIT_RE.match(line)
            if m:
                git = m.group(1).strip()
                continue

        if line.strip() == "| Scenario | Target | Measured | Status | Notes |":
            in_table = True
            continue

        if not in_table:
            continue

        if not line.strip().startswith("|"):
            # End of table.
            break

        # Skip separator row
        if line.strip().startswith("| ---"):
            continue

        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 5:
            continue
        scenario, _target, measured, status, _notes = cols[:5]
        if not scenario:
            continue
        scenarios[scenario] = ScenarioRow(
            name=scenario,
            measured=measured or "-",
            status=status or "UNKNOWN",
        )

    if not started:
        # Fallback to filename timestamp (best-effort).
        started = path.stem.replace("ROADMAP_9_3_", "")
    if not git:
        git = ""

    if not scenarios:
        return None

    return PerfRun(path=path, started=started, git=git, scenarios=scenarios)


def _discover_runs(report_dir: Path) -> List[PerfRun]:
    runs: List[PerfRun] = []
    for path in sorted(report_dir.glob("ROADMAP_9_3_*.md")):
        if path.name == "ROADMAP_9_3_TREND.md":
            continue
        parsed = _parse_report(path)
        if parsed:
            runs.append(parsed)

    def _key(run: PerfRun):
        # Prefer ISO started when possible.
        try:
            return datetime.fromisoformat(run.started.replace("Z", "+00:00"))
        except Exception:
            return run.started

    runs.sort(key=_key, reverse=True)
    return runs


def _cell(run: PerfRun, scenario_name: str) -> str:
    row = run.scenarios.get(scenario_name)
    if not row:
        return "-"
    measured = (row.measured or "-").strip()
    status = (row.status or "UNKNOWN").strip()
    if status.upper() == "SKIP":
        return "SKIP"
    if measured == "-" or not measured:
        return status
    return f"{status} {measured}"


def _write_trend(out_path: Path, runs: List[PerfRun], *, limit: int) -> None:
    scenario_order = [
        "Dedup batch (1000 files) processing",
        "Config BOM calculation (500 levels)",
        "MBOM conversion (1000 lines)",
        "Baseline create (2000 members)",
        "Full-text search response (p95 over 10 runs)",
        "Electronic signature verify (p95 over 20 runs)",
    ]

    now = datetime.now().isoformat(timespec="seconds")
    lines: List[str] = []
    lines.append("# Roadmap 9.3 Performance Trend")
    lines.append("")
    lines.append(f"- Generated: `{now}`")
    lines.append(f"- Source dir: `{out_path.parent.relative_to(REPO_ROOT)}`")
    lines.append(f"- Runs: `{len(runs)}` (showing latest `{min(limit, len(runs))}`)")
    lines.append("")
    lines.append("## Latest Runs")
    lines.append("")

    header = [
        "Started",
        "Git",
        "Overall",
        "Report",
        "Dedup 1000",
        "Config BOM 500",
        "MBOM 1000",
        "Baseline 2000",
        "Search p95",
        "E-sign p95",
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for run in runs[:limit]:
        report_rel = str(run.path.relative_to(REPO_ROOT))
        row = [
            f"`{run.started}`",
            f"`{run.git}`" if run.git else "-",
            run.overall,
            f"`{report_rel}`",
            _cell(run, scenario_order[0]),
            _cell(run, scenario_order[1]),
            _cell(run, scenario_order[2]),
            _cell(run, scenario_order[3]),
            _cell(run, scenario_order[4]),
            _cell(run, scenario_order[5]),
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `SKIP` typically indicates missing optional external dependencies (e.g. Dedup Vision sidecar).")
    lines.append("- Measured values are copied from each per-run report.")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a trend summary for Roadmap 9.3 perf reports")
    parser.add_argument(
        "--dir",
        default=str(REPO_ROOT / "docs" / "PERFORMANCE_REPORTS"),
        help="Directory containing ROADMAP_9_3_*.md reports",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "docs" / "PERFORMANCE_REPORTS" / "ROADMAP_9_3_TREND.md"),
        help="Output markdown path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Number of most recent runs to include",
    )
    args = parser.parse_args()

    report_dir = Path(args.dir).resolve()
    out_path = Path(args.out).resolve()
    limit = max(1, int(args.limit))

    runs = _discover_runs(report_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_trend(out_path, runs, limit=limit)
    print(f"Trend: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

