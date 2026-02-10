# Dev & Verification Report - CI Cost Optimization (Selective Jobs + Perf Gate Summaries) (2026-02-10)

This change reduces wasted CI minutes on PRs that only touch documentation or CI/perf wiring, and improves the usability of perf gating by writing a readable summary to the GitHub Actions step summary.

## Changes

### 1) README: runbooks discoverability

- Expanded the `Runbooks` list in `README.md` so common operational runbooks are one click away.

### 2) Perf workflows: gate results in `GITHUB_STEP_SUMMARY`

- `.github/workflows/perf-p5-reports.yml`
- `.github/workflows/perf-roadmap-9-3.yml`

Both workflows now append a markdown summary that includes:

- which gate profile was used
- candidate report paths (SQLite + Postgres)
- the gate log path
- PASS/FAIL quick verdict + any failing scenarios
- a short tail of the gate log for fast triage

### 3) PR CI: skip heavy jobs when changes are clearly non-runtime

#### `CI` workflow (`.github/workflows/ci.yml`)

- Added a `detect_changes` job that classifies PR changes by file path.
- Added a small `contracts` job (only `pytest`) to validate:
  - perf workflow wiring contracts
  - perf gate config file validity
  - baseline downloader script `--help` contract
  - delivery doc index referenced path existence
- `plugin-tests` and `playwright-esign` are now conditionally executed based on the detected change scope.

#### `regression` workflow (`.github/workflows/regression.yml`)

- Extended `detect_changes` to produce `regression_needed`.
- The expensive docker-compose regression job is skipped on PR/push when no integration-impacting paths changed (docs-only, perf workflow edits, etc.).

## Verification

Local targeted pytest:

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

