#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


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


_STARTED_RE = re.compile(r"^- Started: `([^`]+)`\s*$")
_GIT_RE = re.compile(r"^- Git: `([^`]+)`\s*$")
_DB_RE = re.compile(r"^- DB: `([^`]+)`\s*$")
_DUR_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(ms|s)\s*$", re.IGNORECASE)


def _parse_duration_s(text: str) -> Optional[float]:
    s = (text or "").strip()
    if not s or s == "-":
        return None
    m = _DUR_RE.match(s)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "ms":
        return value / 1000.0
    return value


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


def _parse_started_dt(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _discover_reports(paths: Iterable[Path]) -> List[PerfRun]:
    runs: List[PerfRun] = []
    for path in paths:
        if not path.is_file():
            continue
        parsed = _parse_report(path)
        if parsed:
            runs.append(parsed)

    def _key(run: PerfRun) -> datetime:
        return _parse_started_dt(run.started) or datetime.min

    runs.sort(key=_key, reverse=True)
    return runs


def _baseline_stat(values: List[float], stat: str) -> float:
    if not values:
        return 0.0
    if stat == "median":
        return float(statistics.median(values))
    if stat == "max":
        return float(max(values))
    raise ValueError(f"Unknown baseline stat: {stat}")


def _fmt_ms(seconds: float) -> str:
    return f"{seconds * 1000.0:.1f}ms"


def _gate_one(
    *,
    candidate: PerfRun,
    baselines: List[PerfRun],
    window: int,
    pct: float,
    abs_ms: float,
    stat: str,
) -> Tuple[bool, str]:
    label = _db_label(candidate.db)
    baseline_pool = [r for r in baselines if _db_label(r.db) == label]

    if not baseline_pool:
        return True, f"[gate] candidate={candidate.path} db={label}: no baseline reports found; skipping"

    # Most recent baseline runs first; take a sliding window.
    baseline_window = baseline_pool[: max(1, int(window))]

    abs_s = max(0.0, float(abs_ms) / 1000.0)
    pct = max(0.0, float(pct))

    lines: List[str] = []
    lines.append(
        f"[gate] candidate={candidate.path} db={label} window={len(baseline_window)} stat={stat} pct={pct:.2f} abs={abs_ms:.1f}ms"
    )

    failures: List[str] = []
    for scenario_name, row in sorted(candidate.scenarios.items(), key=lambda kv: kv[0]):
        cand_s = _parse_duration_s(row.measured)
        if cand_s is None:
            lines.append(f"  - {scenario_name}: candidate={row.status} {row.measured} (unparsed); skip")
            continue

        baseline_vals: List[float] = []
        for run in baseline_window:
            base_row = run.scenarios.get(scenario_name)
            if not base_row:
                continue
            v = _parse_duration_s(base_row.measured)
            if v is not None:
                baseline_vals.append(v)

        if not baseline_vals:
            lines.append(f"  - {scenario_name}: candidate={_fmt_ms(cand_s)} baseline=<missing>; skip")
            continue

        base = _baseline_stat(baseline_vals, stat)
        threshold = base * (1.0 + pct)
        delta = cand_s - base

        regressed = bool(cand_s > threshold) and bool(delta >= abs_s)
        verdict = "FAIL" if regressed else "PASS"

        lines.append(
            f"  - {scenario_name}: candidate={_fmt_ms(cand_s)} baseline={_fmt_ms(base)} delta={_fmt_ms(delta)} threshold={_fmt_ms(threshold)} => {verdict}"
        )
        if regressed:
            failures.append(scenario_name)

    if failures:
        lines.append(f"[gate] FAIL scenarios={len(failures)}")
        return False, "\n".join(lines)

    lines.append("[gate] PASS")
    return True, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate P5 reports perf results against a baseline window")
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="Candidate perf report markdown path (repeatable)",
    )
    parser.add_argument(
        "--baseline-dir",
        default="",
        help="Directory containing baseline P5_REPORTS_PERF_*.md reports (searched recursively)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        help="Baseline sliding window size (default: 5)",
    )
    parser.add_argument(
        "--pct",
        type=float,
        default=0.30,
        help="Allowed regression percentage over baseline (default: 0.30)",
    )
    parser.add_argument(
        "--abs-ms",
        type=float,
        default=10.0,
        help="Allowed absolute regression in ms (default: 10ms)",
    )
    parser.add_argument(
        "--baseline-stat",
        choices=["max", "median"],
        default="max",
        help="Statistic used for baseline aggregation (default: max)",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional text output path for gate details (useful for CI artifacts).",
    )
    args = parser.parse_args()

    candidates = [Path(p).resolve() for p in (args.candidate or []) if str(p).strip()]
    if not candidates:
        raise SystemExit("No --candidate reports provided")

    baseline_dir = Path(args.baseline_dir).resolve() if args.baseline_dir else None
    baseline_paths: List[Path] = []
    if baseline_dir and baseline_dir.exists():
        baseline_paths = list(baseline_dir.rglob("P5_REPORTS_PERF_*.md"))

    # Avoid comparing a candidate report against itself when --baseline-dir overlaps.
    cand_set = {p.resolve() for p in candidates}
    baseline_paths = [p for p in baseline_paths if p.resolve() not in cand_set]

    baseline_runs = _discover_reports(baseline_paths)

    out_path = Path(args.out).resolve() if str(args.out or "").strip() else None
    out_chunks: List[str] = []

    ok_all = True
    for cand_path in candidates:
        cand_run = _parse_report(cand_path)
        if not cand_run:
            msg = f"[gate] candidate={cand_path}: not a valid perf report; skip"
            print(msg)
            out_chunks.append(msg)
            continue

        ok, details = _gate_one(
            candidate=cand_run,
            baselines=baseline_runs,
            window=int(args.window),
            pct=float(args.pct),
            abs_ms=float(args.abs_ms),
            stat=str(args.baseline_stat),
        )
        print(details)
        out_chunks.append(details)
        ok_all = ok_all and ok

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n\n".join(out_chunks).rstrip() + "\n", encoding="utf-8")
        print(f"[gate] wrote log: {out_path}")

    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
