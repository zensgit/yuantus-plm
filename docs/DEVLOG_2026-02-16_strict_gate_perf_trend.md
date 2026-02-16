# DEVLOG 2026-02-16: strict-gate perf trend generator

## Scope

Continue strict-gate perf evidence tooling by adding a trend generator that aggregates multiple `STRICT_GATE_*_PERF.md` summaries.

## Changes

1. New script: `scripts/strict_gate_perf_trend.py`
- Reads perf summary markdown files (default glob: `STRICT_GATE_*_PERF.md`) from a target directory.
- Extracts per-run metric cells from the markdown table:
  - `release_orchestration.plan`
  - `release_orchestration.execute_dry_run`
  - `esign.sign`
  - `esign.verify`
  - `esign.audit_summary`
  - `reports.search`
  - `reports.summary`
  - `reports.export`
- Produces trend markdown (default: `docs/DAILY_REPORTS/STRICT_GATE_PERF_TREND.md`):
  - one row per run
  - per-metric cells as `STATUS p95/threshold`
  - run overall status (`PASS` / `FAIL` / `NO_METRICS`)
- Sort order:
  - prefer CI run id (`STRICT_GATE_CI_<id>`) descending
  - fallback to file mtime.
- Defaults to excluding empty runs; use `--include-empty` to keep `NO_METRICS` rows.

2. Runbook update: `docs/RUNBOOK_STRICT_GATE.md`
- Added trend generation command example:
  - `python3 scripts/strict_gate_perf_trend.py --dir ... --out ... --limit ...`

3. Tests
- Added `src/yuantus/meta_engine/tests/test_strict_gate_perf_trend_script.py`:
  - verifies table generation + CI run-id ordering
  - verifies `--include-empty` behavior (`NO_METRICS` rows).
- Updated `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`:
  - runbook contract now requires trend script and output token docs.

## Verification

1. Targeted tests
```bash
.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_strict_gate_perf_trend_script.py \
  src/yuantus/meta_engine/tests/test_strict_gate_perf_summary_script.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py
```

2. Local sample trend generation
```bash
python3 scripts/strict_gate_perf_trend.py \
  --dir docs/DAILY_REPORTS \
  --out tmp/strict-gate/STRICT_GATE_PERF_TREND_LOCAL.md \
  --limit 30
```
