# Dev & Verification Report - P5 Reports/Search Performance Harness (2026-02-08)

This delivery adds a lightweight, reproducible performance harness for Phase 5 (advanced search + reports).

## Runner

- Script: `scripts/perf_p5_reports.py`
- Trend generator: `scripts/perf_p5_reports_trend.py`
- Baseline gate: `scripts/perf_p5_reports_gate.py` (compare candidate report(s) vs recent baselines)
- Output directory: `docs/PERFORMANCE_REPORTS/`

## Scenarios

- Reports summary (p95 over 10 runs)
- Reports advanced search response (p95 over 10 runs)
- Saved search run (p95 over 10 runs)
- Report execute (p95 over 5 runs)
- Report export CSV (p95 over 5 runs)

## CI Schedule

- Workflow: `.github/workflows/perf-p5-reports.yml`
  - Weekly on Sunday 05:00 UTC
  - Runs the harness on SQLite and Postgres; uploads per-run reports and a trend snapshot as workflow artifacts (does not commit to git).
  - Downloads recent successful run artifacts as baselines and gates the current run (fails the workflow on regression beyond tolerance).

## Usage

Run locally (default SQLite under `tmp/perf/`):

```bash
./.venv/bin/python scripts/perf_p5_reports.py
./.venv/bin/python scripts/perf_p5_reports_trend.py
```

Run against Postgres (example):

```bash
PG_URL='postgresql+psycopg://yuantus:yuantus@localhost:5432/yuantus_perf'
./.venv/bin/python scripts/perf_p5_reports.py --db-url "$PG_URL"
./.venv/bin/python scripts/perf_p5_reports_trend.py
```

Gate a candidate run against a local baseline directory (example):

```bash
python scripts/perf_p5_reports_gate.py \
  --candidate docs/PERFORMANCE_REPORTS/P5_REPORTS_PERF_20260208-211413.md \
  --baseline-dir docs/PERFORMANCE_REPORTS \
  --window 5 \
  --pct 0.30 \
  --abs-ms 10
```

## Evidence

- Latest report: `docs/PERFORMANCE_REPORTS/P5_REPORTS_PERF_20260208-211413.md`
- Trend: `docs/PERFORMANCE_REPORTS/P5_REPORTS_PERF_TREND.md`
