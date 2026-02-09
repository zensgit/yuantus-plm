# Roadmap 9.3 Perf CI (SQLite + Postgres) - Dev Plan & Verification (2026-02-09)

## Goal

Make the `perf-roadmap-9-3` GitHub Actions workflow run the Roadmap 9.3 performance harness against **both SQLite and Postgres**, and keep the same baseline-gated regression policy for each DB. Also update the Roadmap 9.3 trend generator to show a DB label column.

## Implementation Plan (What Changed)

### 1) CI workflow: add Postgres run + artifacts + baseline download

- File: `.github/workflows/perf-roadmap-9-3.yml`
- Added `services.postgres` (postgres:16) with health check.
- Added a second benchmark step:
  - SQLite report: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_CI_${{ github.run_id }}.md`
  - Postgres report: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_PG_CI_${{ github.run_id }}.md`
  - Postgres URL (GitHub-hosted runner): `postgresql+psycopg://yuantus:yuantus@localhost:5432/yuantus_perf`
- Baseline download now fetches both artifacts from recent successful runs:
  - `perf-roadmap-9-3-report`
  - `perf-roadmap-9-3-report-pg`
- Gate step now gates **two candidates** in one invocation and writes one log:
  - `python scripts/perf_gate.py --candidate <sqlite> --candidate <pg> ... --out <gate_log>`
- Uploads additional artifact:
  - `perf-roadmap-9-3-report-pg`

### 2) Trend: add DB column

- File: `scripts/perf_roadmap_9_3_trend.py`
- Parse `- DB: `...`` from each per-run report and infer a short DB label (`sqlite`, `postgres`, etc.).
- Add a `DB` column to the trend table.

### 3) Regenerate tracked trend markdown

- File: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_TREND.md`
- Re-generated using the updated trend script.

## CI Artifacts (Workflow Outputs)

When `perf-roadmap-9-3` runs, it should publish:

- `perf-roadmap-9-3-report` (SQLite per-run report)
- `perf-roadmap-9-3-report-pg` (Postgres per-run report)
- `perf-roadmap-9-3-gate` (gate log comparing candidates to baseline window)
- `perf-roadmap-9-3-trend` (trend snapshot produced during the run)

## Gate Policy Details

The gate is implemented by `scripts/perf_gate.py` (with `scripts/perf_p5_reports_gate.py` kept as a backward-compatible wrapper) and configured in CI as:

- baseline window: `5` recent successful workflow runs
- baseline stat: `max`
- allowed regression (sqlite): `+30%` AND `>= 10ms` absolute regression
- allowed regression (postgres): `+50%` AND `>= 15ms` absolute regression

Important: gating is **DB-aware**. The gate script infers a DB label from each report’s `- DB:` URL and only compares candidates against baseline reports with the same DB label (sqlite vs postgres).

## PR Trigger (Paths Filter)

`perf-roadmap-9-3` also runs on pull requests when perf-related files change (paths filter in `.github/workflows/perf-roadmap-9-3.yml`).

## Verification (Executed)

### Local smoke verification (SQLite + Postgres)

This repo was verified by running the harness twice (forcing Dedup Vision to `SKIP` so the run stays fast) and then regenerating the trend:

- SQLite report: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260209-000914.md`
- Postgres report: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_PG_20260209-001013.md`
- Trend: `docs/PERFORMANCE_REPORTS/ROADMAP_9_3_TREND.md`

Commands used (reference):

```bash
docker run -d --name yuantus-roadmap93-pg \
  -e POSTGRES_USER=yuantus \
  -e POSTGRES_PASSWORD=yuantus \
  -e POSTGRES_DB=yuantus_perf \
  -p 55432:5432 \
  postgres:16

YUANTUS_DEDUP_VISION_BASE_URL=http://example.invalid:8100 \
  python3 scripts/perf_roadmap_9_3.py \
  --out docs/PERFORMANCE_REPORTS/ROADMAP_9_3_20260209-000914.md

YUANTUS_DEDUP_VISION_BASE_URL=http://example.invalid:8100 \
  python3 scripts/perf_roadmap_9_3.py \
  --db-url postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_perf \
  --out docs/PERFORMANCE_REPORTS/ROADMAP_9_3_PG_20260209-001013.md

python3 scripts/perf_roadmap_9_3_trend.py \
  --out docs/PERFORMANCE_REPORTS/ROADMAP_9_3_TREND.md

docker rm -f yuantus-roadmap93-pg
```

### Script sanity

```bash
python3 -m py_compile scripts/perf_roadmap_9_3_trend.py scripts/perf_gate.py scripts/perf_p5_reports_gate.py
```

### CI verification (workflow_dispatch)

- Workflow: `perf-roadmap-9-3`
- Pre-merge run (branch): `21801294326` (success)
- Post-merge run (main): `21801412881` (success)
- PR check run (PR #76): `21814459189` (success)
- Main run (post #76, workflow_dispatch): `21821935636` (success)
- Artifacts:
  - `perf-roadmap-9-3-report`
  - `perf-roadmap-9-3-report-pg`
  - `perf-roadmap-9-3-gate`
  - `perf-roadmap-9-3-trend`

## Notes / Known Behavior

- In CI, the Dedup Vision sidecar is typically unavailable; the dedup scenario will usually show `SKIP`. This is expected and is treated as non-failing for trend and gating purposes.
