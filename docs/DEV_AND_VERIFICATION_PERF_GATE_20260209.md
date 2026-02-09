# Perf Gate (Generic) - Dev Plan & Verification (2026-02-09)

This change extracts a generic performance baseline gate into a reusable script and wires it into CI.

## Goal

- Use one gate implementation across perf harnesses (P5 + Roadmap 9.3).
- Keep gating DB-aware (SQLite baselines compare with SQLite candidates; Postgres with Postgres).
- Allow **DB-specific thresholds** (Postgres tends to be noisier on GitHub-hosted runners).
- Keep perf CI workflow YAML lean by centralizing thresholds in a config file.
- Reuse baseline artifact download logic across perf workflows.
- Avoid wasted CI by canceling in-progress runs per ref.

## What Changed

### 1) Generic gate entrypoint

- Script: `scripts/perf_gate.py`
- Inputs:
  - Optional config:
    - `--config <path>` (JSON file)
    - `--profile <name>` (select a named config profile, e.g. `p5_reports`, `roadmap_9_3`)
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
  - When `--config/--profile` are used, resolves thresholds with precedence:
    - CLI flags > profile values > config defaults > built-in defaults.

### 2) Backward compatibility

- Wrapper kept: `scripts/perf_p5_reports_gate.py`
- Existing invocations continue to work; wrapper just calls `scripts/perf_gate.py` logic with historical defaults.

### 3) CI wiring

- `.github/workflows/perf-p5-reports.yml`
  - Baselines are downloaded with `scripts/perf_ci_download_baselines.sh` (best-effort).
  - Gate now uses `python scripts/perf_gate.py --config configs/perf_gate.json --profile p5_reports ...`
  - Adds `concurrency.cancel-in-progress` to reduce wasted CI on rapid PR pushes.
- `.github/workflows/perf-roadmap-9-3.yml`
  - Adds `pull_request` trigger (paths filter) so perf runs on relevant PRs.
  - Baselines are downloaded with `scripts/perf_ci_download_baselines.sh` (best-effort).
  - Gate now uses `python scripts/perf_gate.py --config configs/perf_gate.json --profile roadmap_9_3 ...`
  - Adds `concurrency.cancel-in-progress` to reduce wasted CI on rapid PR pushes.

### 4) Baseline artifact downloader (CI helper)

- Script: `scripts/perf_ci_download_baselines.sh`
- Goal: download baseline artifacts from the latest successful runs of a workflow (best-effort).
- Used by:
  - `perf-p5-reports` (downloads SQLite + Postgres perf report artifacts)
  - `perf-roadmap-9-3` (downloads SQLite + Postgres perf report artifacts)

### 5) Gate config (single source of thresholds)

- Config: `configs/perf_gate.json`
- Contains:
  - `defaults`: baseline window/stat + default thresholds
  - `db_overrides`: per-DB thresholds (currently `postgres`)
  - `profiles`: per-harness `baseline_glob` (and optional threshold overrides)

## Verification

### Local sanity

```bash
python3 -m py_compile scripts/perf_gate.py scripts/perf_p5_reports_gate.py
pytest -q src/yuantus/meta_engine/tests/test_perf_gate_cli.py
```

### CI evidence

- PR checks (PR #76):
  - `perf-p5-reports` run `21814459187` (success)
  - `perf-roadmap-9-3` run `21814459189` (success)
- Main runs (workflow_dispatch):
  - `perf-p5-reports` run `21821935491` (success)
  - `perf-roadmap-9-3` run `21821935636` (success)
