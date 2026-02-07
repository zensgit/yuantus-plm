# Dev & Verification Report - Roadmap 9.3 Performance Benchmarks (2026-02-07)

This delivery adds an automated benchmark harness for roadmap section 9.3 performance targets:

- Batch dedup 1000 files (< 10m)
- Config BOM calculation 500 levels (< 5s)
- MBOM conversion 1000 lines (< 30s)
- Baseline create 2000 members (< 1m)
- Full-text search response (< 500ms)
- E-sign verify (< 100ms)

## Runner

- Script: `scripts/perf_roadmap_9_3.py`
- Output: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_*.md`

## Evidence (Latest)

- `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260207-135822.md` (PASS 6/6)
- Strict gate:
  - `docs/DAILY_REPORTS/STRICT_GATE_20260207-140604.md` (PASS)

Notes:
- Harness is in-process SQLAlchemy for most scenarios; dedup batch processing uses HTTP calls to a Dedup Vision sidecar when available.
- The harness forces an isolated local storage root under `tmp/perf/storage_<timestamp>` to avoid polluting dev data.
