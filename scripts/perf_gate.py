#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
        # Best-effort fallback.
        started = path.stem

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

    baseline_window = baseline_pool[: max(1, int(window))]

    abs_s = max(0.0, float(abs_ms) / 1000.0)
    pct = max(0.0, float(pct))

    lines: List[str] = []
    lines.append(
        f"[gate] candidate={candidate.path} db={label} window={len(baseline_window)} "
        f"stat={stat} pct={pct:.2f} abs={abs_ms:.1f}ms"
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
            f"  - {scenario_name}: candidate={_fmt_ms(cand_s)} baseline={_fmt_ms(base)} "
            f"delta={_fmt_ms(delta)} threshold={_fmt_ms(threshold)} => {verdict}"
        )
        if regressed:
            failures.append(scenario_name)

    if failures:
        lines.append(f"[gate] FAIL scenarios={len(failures)}")
        return False, "\n".join(lines)

    lines.append("[gate] PASS")
    return True, "\n".join(lines)


def _parse_db_overrides(items: Iterable[str], *, flag_name: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for raw in items:
        s = (raw or "").strip()
        if not s:
            continue
        if "=" not in s:
            raise SystemExit(f"Invalid {flag_name} '{raw}'; expected <db>=<float> (example: postgres=0.50)")
        key, value = s.split("=", 1)
        label = key.strip().lower()
        if not label:
            raise SystemExit(f"Invalid {flag_name} '{raw}'; missing db label")
        try:
            out[label] = float(value.strip())
        except ValueError:
            raise SystemExit(f"Invalid {flag_name} '{raw}'; value must be a number")
    return out


def _load_config(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in --config {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid --config {path}: expected a JSON object")
    return data


def _as_int(value, *, field: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise SystemExit(f"Invalid config field '{field}': expected int") from exc


def _as_float(value, *, field: str) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise SystemExit(f"Invalid config field '{field}': expected number") from exc


def main(argv: Optional[List[str]] = None, *, default_baseline_glob: str = "*.md") -> int:
    parser = argparse.ArgumentParser(description="Gate perf reports against a baseline window")
    parser.add_argument(
        "--config",
        default="",
        help="Optional JSON config file for defaults and per-DB overrides.",
    )
    parser.add_argument(
        "--profile",
        default="",
        help="Optional config profile name (e.g. p5_reports, roadmap_9_3).",
    )
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        help="Candidate perf report markdown path (repeatable)",
    )
    parser.add_argument(
        "--baseline-dir",
        default="",
        help="Directory containing baseline perf report markdown files (searched recursively)",
    )
    parser.add_argument(
        "--baseline-glob",
        default=None,
        help=f"Baseline report glob (searched recursively under --baseline-dir). Default: {default_baseline_glob}",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=None,
        help="Baseline sliding window size (default: 5; can be set in --config).",
    )
    parser.add_argument(
        "--pct",
        type=float,
        default=None,
        help="Allowed regression percentage over baseline (default: 0.30; can be set in --config).",
    )
    parser.add_argument(
        "--abs-ms",
        type=float,
        default=None,
        help="Allowed absolute regression in ms (default: 10ms; can be set in --config).",
    )
    parser.add_argument(
        "--db-pct",
        action="append",
        default=[],
        help="Override --pct per DB label (repeatable). Example: --db-pct postgres=0.50",
    )
    parser.add_argument(
        "--db-abs-ms",
        action="append",
        default=[],
        help="Override --abs-ms per DB label (repeatable). Example: --db-abs-ms postgres=15",
    )
    parser.add_argument(
        "--baseline-stat",
        choices=["max", "median"],
        default=None,
        help="Statistic used for baseline aggregation (default: max; can be set in --config).",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional text output path for gate details (useful for CI artifacts).",
    )
    args = parser.parse_args(argv)

    candidates = [Path(p).resolve() for p in (args.candidate or []) if str(p).strip()]
    if not candidates:
        raise SystemExit("No --candidate reports provided")

    config: Dict = {}
    profile: Dict = {}
    if str(args.config or "").strip():
        config_path = Path(args.config).resolve()
        config = _load_config(config_path)

        profiles = config.get("profiles", {})
        if args.profile:
            if not isinstance(profiles, dict):
                raise SystemExit("Invalid --config: 'profiles' must be an object")
            if str(args.profile) not in profiles:
                raise SystemExit(f"Unknown --profile '{args.profile}' in --config {config_path}")
            profile = profiles.get(str(args.profile)) or {}
            if not isinstance(profile, dict):
                raise SystemExit(f"Invalid --config: profile '{args.profile}' must be an object")

    defaults = config.get("defaults", {}) if config else {}
    if defaults and not isinstance(defaults, dict):
        raise SystemExit("Invalid --config: 'defaults' must be an object")

    # Resolve effective base thresholds from: CLI > profile > defaults > built-in defaults.
    window = int(args.window) if args.window is not None else None
    pct = float(args.pct) if args.pct is not None else None
    abs_ms = float(args.abs_ms) if args.abs_ms is not None else None
    baseline_stat = str(args.baseline_stat) if args.baseline_stat is not None else None

    if window is None:
        if "window" in profile:
            window = _as_int(profile.get("window"), field="profiles.<name>.window")
        elif "window" in defaults:
            window = _as_int(defaults.get("window"), field="defaults.window")
        else:
            window = 5
    window = max(1, int(window))

    if baseline_stat is None:
        if "baseline_stat" in profile:
            baseline_stat = str(profile.get("baseline_stat"))
        elif "baseline_stat" in defaults:
            baseline_stat = str(defaults.get("baseline_stat"))
        else:
            baseline_stat = "max"
    if baseline_stat not in {"max", "median"}:
        raise SystemExit(f"Invalid baseline_stat: {baseline_stat} (expected max|median)")

    if pct is None:
        if "pct" in profile:
            pct = _as_float(profile.get("pct"), field="profiles.<name>.pct")
        elif "pct" in defaults:
            pct = _as_float(defaults.get("pct"), field="defaults.pct")
        else:
            pct = 0.30

    if abs_ms is None:
        if "abs_ms" in profile:
            abs_ms = _as_float(profile.get("abs_ms"), field="profiles.<name>.abs_ms")
        elif "abs_ms" in defaults:
            abs_ms = _as_float(defaults.get("abs_ms"), field="defaults.abs_ms")
        else:
            abs_ms = 10.0

    cfg_glob: Optional[str] = None
    if "baseline_glob" in profile:
        cfg_glob = str(profile.get("baseline_glob") or "").strip() or None
    elif config and "baseline_glob" in config:
        cfg_glob = str(config.get("baseline_glob") or "").strip() or None
    baseline_glob = (str(args.baseline_glob).strip() if args.baseline_glob is not None else "") or (cfg_glob or "")
    baseline_glob = baseline_glob or default_baseline_glob

    cfg_db_overrides: Dict[str, Dict] = {}
    if config and "db_overrides" in config:
        if not isinstance(config.get("db_overrides"), dict):
            raise SystemExit("Invalid --config: 'db_overrides' must be an object")
        cfg_db_overrides.update(config.get("db_overrides") or {})
    if profile and "db_overrides" in profile:
        if not isinstance(profile.get("db_overrides"), dict):
            raise SystemExit("Invalid --config: profile 'db_overrides' must be an object")
        cfg_db_overrides.update(profile.get("db_overrides") or {})

    cfg_pct_overrides: Dict[str, float] = {}
    cfg_abs_overrides: Dict[str, float] = {}
    for label_raw, ov in cfg_db_overrides.items():
        if not isinstance(ov, dict):
            raise SystemExit("Invalid --config: db_overrides values must be objects")
        label = str(label_raw).strip().lower()
        if not label:
            continue
        if "pct" in ov:
            cfg_pct_overrides[label] = _as_float(ov.get("pct"), field=f"db_overrides.{label}.pct")
        if "abs_ms" in ov:
            cfg_abs_overrides[label] = _as_float(ov.get("abs_ms"), field=f"db_overrides.{label}.abs_ms")

    # CLI overrides take precedence over config overrides.
    pct_overrides = {**cfg_pct_overrides, **_parse_db_overrides(args.db_pct or [], flag_name="--db-pct")}
    abs_overrides = {**cfg_abs_overrides, **_parse_db_overrides(args.db_abs_ms or [], flag_name="--db-abs-ms")}

    baseline_dir = Path(args.baseline_dir).resolve() if args.baseline_dir else None
    baseline_paths: List[Path] = []
    if baseline_dir and baseline_dir.exists():
        baseline_paths = list(baseline_dir.rglob(baseline_glob))

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

        label = _db_label(cand_run.db)
        pct_for_db = pct_overrides.get(label, float(pct))
        abs_ms_for_db = abs_overrides.get(label, float(abs_ms))

        ok, details = _gate_one(
            candidate=cand_run,
            baselines=baseline_runs,
            window=int(window),
            pct=float(pct_for_db),
            abs_ms=float(abs_ms_for_db),
            stat=str(baseline_stat),
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
