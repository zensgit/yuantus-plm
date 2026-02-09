# Perf Gate (Generic) - Dev Plan & Verification (2026-02-09)

This change extracts a generic performance baseline gate into a reusable script and wires it into CI.

## Goal

- Use one gate implementation across perf harnesses (P5 + Roadmap 9.3).
- Keep gating DB-aware (SQLite baselines compare with SQLite candidates; Postgres with Postgres).
- Allow **DB-specific thresholds** (Postgres tends to be noisier on GitHub-hosted runners).

## What Changed

### 1) Generic gate entrypoint

- Script: `scripts/perf_gate.py`
- Inputs:
  - `--candidate <path>` (repeatable)
  - `--baseline-dir <dir>` + `--baseline-glob <glob>` (searched recursively)
  - `--window <n>` + `--baseline-stat max|median`
  - `--pct <float>` + `--abs-ms <float>`
  - Per-DB overrides:
    - `--db-pct <db>=<float>` (repeatable, e.g. `postgres=0.50`)
    - `--db-abs-ms <db>=<float>` (repeatable, e.g. `postgres=15`)
- Behavior:
  - Infers DB label from report header `- DB: `...``.
  - Filters baseline pool by DB label before gating.

### 2) Backward compatibility

- Wrapper kept: `scripts/perf_p5_reports_gate.py`
- Existing invocations continue to work; wrapper just calls `scripts/perf_gate.py` logic with historical defaults.

### 3) CI wiring

- `.github/workflows/perf-p5-reports.yml`
  - Gate now uses `python scripts/perf_gate.py ... --baseline-glob "P5_REPORTS_PERF_*.md"`
  - Postgres overrides in CI:
    - `--db-pct postgres=0.50`
    - `--db-abs-ms postgres=15`
- `.github/workflows/perf-roadmap-9-3.yml`
  - Adds `pull_request` trigger (paths filter) so perf runs on relevant PRs.
  - Gate now uses `python scripts/perf_gate.py ... --baseline-glob "ROADMAP_9_3_*.md"`
  - Same Postgres overrides as above.

## Verification

### Local sanity

```bash
python3 -m py_compile scripts/perf_gate.py scripts/perf_p5_reports_gate.py
```

### CI evidence

- PR checks (PR #76):
  - `perf-p5-reports` run `21814459187` (success)
  - `perf-roadmap-9-3` run `21814459189` (success)
- Main runs (workflow_dispatch):
  - `perf-p5-reports` run `21821935491` (success)
  - `perf-roadmap-9-3` run `21821935636` (success)

