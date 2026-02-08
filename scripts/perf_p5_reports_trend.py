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
    db: str
    scenarios: Dict[str, ScenarioRow]

    @property
    def overall(self) -> str:
        statuses = {row.status for row in self.scenarios.values()}
        if "FAIL" in statuses:
            return "FAIL"
        return "PASS"


_STARTED_RE = re.compile(r"^- Started: `([^`]+)`\s*$")
_GIT_RE = re.compile(r"^- Git: `([^`]+)`\s*$")
_DB_RE = re.compile(r"^- DB: `([^`]+)`\s*$")


def _parse_report(path: Path) -> Optional[PerfRun]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    started = ""
    git = ""
    db = ""
    scenarios: Dict[str, ScenarioRow] = {}
    in_table = False

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
        if not db:
            m = _DB_RE.match(line)
            if m:
                db = m.group(1).strip()
                continue

        if line.strip() == "| Scenario | Target | Measured | Status | Notes |":
            in_table = True
            continue

        if not in_table:
            continue

        if not line.strip().startswith("|"):
            break

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
        started = path.stem.replace("P5_REPORTS_PERF_", "")

    if not scenarios:
        return None

    return PerfRun(path=path, started=started, git=git, db=db, scenarios=scenarios)


def _db_label(db: str) -> str:
    raw = (db or "").strip()
    if not raw:
        return "-"
    s = raw.lower()
    if s.startswith("sqlite:"):
        return "sqlite"
    if s.startswith("postgresql") or s.startswith("postgres:"):
        return "postgres"
    if s.startswith("mysql"):
        return "mysql"
    return raw.split(":", 1)[0] if ":" in raw else raw


def _discover_runs(report_dir: Path) -> List[PerfRun]:
    runs: List[PerfRun] = []
    for path in sorted(report_dir.glob("P5_REPORTS_PERF_*.md")):
        if path.name == "P5_REPORTS_PERF_TREND.md":
            continue
        parsed = _parse_report(path)
        if parsed:
            runs.append(parsed)

    def _key(run: PerfRun):
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
    if measured == "-" or not measured:
        return status
    return f"{status} {measured}"


def _write_trend(out_path: Path, runs: List[PerfRun], *, report_dir: Path, limit: int) -> None:
    scenario_order = [
        "Reports summary (p95 over 10 runs)",
        "Reports advanced search response (p95 over 10 runs)",
        "Saved search run (p95 over 10 runs)",
        "Report execute (p95 over 5 runs)",
        "Report export CSV (p95 over 5 runs)",
    ]

    now = datetime.now().isoformat(timespec="seconds")
    lines: List[str] = []
    lines.append("# Phase 5 Reports/Search Performance Trend")
    lines.append("")
    lines.append(f"- Generated: `{now}`")
    # Allow --dir outside the repo as well.
    try:
        source_dir = report_dir.relative_to(REPO_ROOT)
    except ValueError:
        source_dir = report_dir
    lines.append(f"- Source dir: `{source_dir}`")
    lines.append(f"- Runs: `{len(runs)}` (showing latest `{min(limit, len(runs))}`)")
    lines.append("")
    lines.append("## Latest Runs")
    lines.append("")

    header = [
        "Started",
        "Git",
        "DB",
        "Overall",
        "Report",
        "Reports summary p95",
        "Reports search p95",
        "Saved search p95",
        "Report execute p95",
        "Report export p95",
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for run in runs[:limit]:
        try:
            report_rel = str(run.path.relative_to(REPO_ROOT))
        except ValueError:
            report_rel = str(run.path)
        row = [
            f"`{run.started}`",
            f"`{run.git}`" if run.git else "-",
            f"`{_db_label(run.db)}`",
            run.overall,
            f"`{report_rel}`",
            _cell(run, scenario_order[0]),
            _cell(run, scenario_order[1]),
            _cell(run, scenario_order[2]),
            _cell(run, scenario_order[3]),
            _cell(run, scenario_order[4]),
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Measured values are copied from each per-run report.")
    lines.append("- DB is inferred from the per-run report DB URL.")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a trend summary for P5 reports perf reports")
    parser.add_argument(
        "--dir",
        default=str(REPO_ROOT / "docs" / "PERFORMANCE_REPORTS"),
        help="Directory containing P5_REPORTS_PERF_*.md reports",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "docs" / "PERFORMANCE_REPORTS" / "P5_REPORTS_PERF_TREND.md"),
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
    _write_trend(out_path, runs, report_dir=report_dir, limit=limit)
    print(f"Trend: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
