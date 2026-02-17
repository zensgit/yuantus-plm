# DEVLOG 2026-02-16: strict-gate perf artifact download helper

## Scope

Add a CLI helper that pulls recent strict-gate perf summary artifacts via `gh` and generates a local trend report in one command. The helper now also supports a custom artifact name through `--artifact-name`.

## Changes

1. New helper script: `scripts/strict_gate_perf_download_and_trend.sh`
- Purpose:
  - list recent strict-gate runs
  - download a configured artifact (default: `strict-gate-perf-summary`)
  - call `scripts/strict_gate_perf_trend.py` to generate trend markdown
- Inputs:
  - `--limit` (default `10`)
  - `--run-id` (optional; explicit run id(s), comma-separated supported)
  - `--workflow` (default `strict-gate`)
  - `--branch` (default `main`)
  - `--conclusion` (default `any`; supports `any|success|failure`)
  - `--artifact-name` (default `strict-gate-perf-summary`)
  - `--download-retries` (default `1`; retry attempts per run download)
  - `--download-retry-delay-sec` (default `1`; retry delay in seconds)
  - `--clean-download-dir` (optional; clear download dir before downloading)
  - `--fail-if-none-downloaded` (optional; exit non-zero when downloaded count is 0)
  - `--download-dir` (default `tmp/strict-gate-artifacts/recent-perf`)
  - `--trend-out` (default `<download-dir>/STRICT_GATE_PERF_TREND.md`)
  - `--json-out` (optional JSON summary path for automation)
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
- Added `src/yuantus/meta_engine/tests/test_strict_gate_perf_download_and_trend_script.py`:
  - uses a fake `gh` binary to simulate `run list` + `run download`
  - validates downloaded artifact counting and generated trend ordering/content
  - validates custom `--artifact-name` is forwarded to `gh run download -n`
  - validates retry behavior (`--download-retries` + `--download-retry-delay-sec`)
  - validates `--clean-download-dir` removes stale downloaded reports before trend generation
  - validates `--fail-if-none-downloaded` exits with non-zero when all downloads fail
  - validates `--conclusion success` only keeps success runs
  - validates `--run-id` mode bypasses `run list` and downloads explicit run ids
  - validates `--json-out` output fields (counts + selected/downloaded/skipped ids)
- Updated `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`:
  - runbook token now requires `strict_gate_perf_download_and_trend.sh`

## Verification

1. Shell syntax + help contracts + strict-gate contracts
```bash
.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_strict_gate_perf_download_and_trend_script.py \
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

3. End-to-end helper smoke (real gh download + trend output)
```bash
bash scripts/strict_gate_perf_download_and_trend.sh \
  --limit 1 \
  --branch main \
  --conclusion failure \
  --artifact-name strict-gate-perf-summary \
  --download-dir tmp/strict-gate-artifacts/recent-perf-smoke \
  --trend-out tmp/strict-gate-artifacts/recent-perf-smoke/STRICT_GATE_PERF_TREND.md \
  --include-empty
```
Result: artifact download succeeded and trend markdown generated.

4. Real helper smoke for `--run-id` mode
```bash
bash scripts/strict_gate_perf_download_and_trend.sh \
  --run-id 22085198707 \
  --download-dir tmp/strict-gate-artifacts/recent-perf-smoke-runid \
  --trend-out tmp/strict-gate-artifacts/recent-perf-smoke-runid/STRICT_GATE_PERF_TREND.md \
  --json-out tmp/strict-gate-artifacts/recent-perf-smoke-runid/strict_gate_perf_download.json \
  --include-empty
```
