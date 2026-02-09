# Perf CI Refactor (Config + Baselines + Concurrency) - Dev Plan & Verification (2026-02-09)

This change refactors perf CI plumbing so both perf workflows share baseline-download logic, read gate thresholds from a single config file, and cancel redundant runs on rapid pushes.

## Goals

- Reduce YAML duplication in perf workflows.
- Keep thresholds in one place (config) while preserving CLI overrides.
- Make baseline download best-effort and reusable across workflows.
- Reduce wasted CI minutes by canceling in-progress runs for the same ref.

## Scope

- Workflows:
  - `.github/workflows/perf-p5-reports.yml`
  - `.github/workflows/perf-roadmap-9-3.yml`
- Gate implementation:
  - `scripts/perf_gate.py`
  - `scripts/perf_p5_reports_gate.py` (compat wrapper, unchanged behavior)
- New shared assets:
  - `scripts/perf_ci_download_baselines.sh`
  - `configs/perf_gate.json`
- Runbook:
  - `docs/RUNBOOK_PERF_GATE_CONFIG.md`

## Implementation (What Changed)

### 1) Shared baseline downloader

- Added `scripts/perf_ci_download_baselines.sh`.
- Downloads named artifact(s) from the latest successful runs of a given workflow on `main`.
- Best-effort behavior:
  - If no runs/artifacts are found (or API calls fail), the script exits 0 and the workflow continues without baselines.

### 2) Config-driven gate defaults (optional)

- Added `configs/perf_gate.json`:
  - `defaults`: `window`, `baseline_stat`, `pct`, `abs_ms`
  - `db_overrides`: per-DB thresholds (currently `postgres`)
  - `profiles`: per-harness `baseline_glob` (currently `p5_reports`, `roadmap_9_3`)
- Updated `scripts/perf_gate.py` to accept:
  - `--config <path>` and `--profile <name>`
  - Precedence: CLI flags > profile values > config defaults > built-in defaults.
- Existing CLI flags (including `--db-pct/--db-abs-ms`) still work and override config.

### 3) Workflow wiring

- Updated both perf workflows to:
  - Download baselines using `scripts/perf_ci_download_baselines.sh`.
  - Invoke gate using `--config configs/perf_gate.json --profile <profile>`.
  - Add `concurrency.cancel-in-progress: true` per workflow/ref.
  - Extend `pull_request.paths` to include the new config/script so CI runs when those change.

## Verification

### Local sanity (executed)

```bash
python3 -m py_compile scripts/perf_gate.py scripts/perf_p5_reports_gate.py
pytest -q src/yuantus/meta_engine/tests/test_perf_gate_cli.py
pytest -q src/yuantus/meta_engine/tests/test_perf_gate_config_file.py
pytest -q src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py
pytest -q src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py
```

### CI evidence

- PR checks (PR #79):
  - `perf-p5-reports`: run `21823036492` (success)
  - `perf-roadmap-9-3`: run `21823036504` (success)
- Main runs (workflow_dispatch, post-refactor):
  - `perf-p5-reports`: run `21832779252` (success)
  - `perf-roadmap-9-3`: run `21832780373` (success)
