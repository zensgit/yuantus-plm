# DEVLOG 2026-02-16: strict-gate perf artifact download helper

## Scope

Add a CLI helper that pulls recent strict-gate perf summary artifacts via `gh` and generates a local trend report in one command.

## Changes

1. New helper script: `scripts/strict_gate_perf_download_and_trend.sh`
- Purpose:
  - list recent strict-gate runs
  - download `strict-gate-perf-summary` artifacts
  - call `scripts/strict_gate_perf_trend.py` to generate trend markdown
- Inputs:
  - `--limit` (default `10`)
  - `--workflow` (default `strict-gate`)
  - `--branch` (default `main`)
  - `--download-dir` (default `tmp/strict-gate-artifacts/recent-perf`)
  - `--trend-out` (default `<download-dir>/STRICT_GATE_PERF_TREND.md`)
  - `--include-empty`
  - `--repo` (optional `owner/repo`, passed to gh `-R`)
- Safety checks:
  - validates `gh`/`python3` presence
  - validates `gh auth status`
  - validates limit is positive integer

2. Runbook update: `docs/RUNBOOK_STRICT_GATE.md`
- Added one-command example to fetch recent perf artifacts and generate trend.
- Explicitly notes `gh auth login` prerequisite.

3. Tests
- Updated `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`:
  - include `strict_gate_perf_download_and_trend.sh` in `bash -n` syntax list
  - add help-contract test for script (`--help` output tokens)
- Updated `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`:
  - runbook token now requires `strict_gate_perf_download_and_trend.sh`

## Verification

1. Shell syntax + help contracts + strict-gate contracts
```bash
.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_strict_gate_perf_trend_script.py \
  src/yuantus/meta_engine/tests/test_strict_gate_perf_summary_script.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py
```

2. Local helper help smoke
```bash
bash scripts/strict_gate_perf_download_and_trend.sh --help
```
