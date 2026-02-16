# DEVLOG 2026-02-16: strict-gate perf summary artifact + job summary

## Scope

Continue strict-gate CI hardening by automatically aggregating perf-smoke metrics into a compact Markdown summary per run.

## Changes

1. New script: `scripts/strict_gate_perf_summary.py`
- Input: strict-gate logs dir (for example `tmp/strict-gate/STRICT_GATE_CI_<run_id>`).
- Reads known perf metric files:
  - `verify-release-orchestration-perf/metrics_summary.json`
  - `verify-esign-perf/metrics_summary.json`
  - `verify-reports-perf/metrics_summary.json`
- Emits markdown table rows with:
  - metric label
  - PASS/FAIL/UNKNOWN (from `p95_ms` vs `threshold_ms`)
  - `p95_ms`, `threshold_ms`, samples
  - source path
- If metrics are absent (perf steps skipped/failed before metrics), emits a clear note instead of failing.

2. Workflow integration: `.github/workflows/strict-gate.yml`
- Added `Build strict gate perf summary` step (`if: always()`):
  - `python3 scripts/strict_gate_perf_summary.py ...`
  - writes `docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>_PERF.md`
  - appends generated markdown to `$GITHUB_STEP_SUMMARY`
- Added new artifact upload:
  - `strict-gate-perf-summary`
  - path: `docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>_PERF.md`
- Updated download hints to include `strict-gate-perf-summary`.

3. Runbook updates: `docs/RUNBOOK_STRICT_GATE.md`
- Added perf summary to evidence outputs.
- Added artifact download command for `strict-gate-perf-summary`.
- Added local command example to generate perf summary from logs:
  - `python3 scripts/strict_gate_perf_summary.py --logs-dir ... --out ...`

4. CI contract updates: `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`
- Added workflow assertions for:
  - perf summary build step + env path
  - new artifact name/path
- Added runbook token requirements for:
  - `strict-gate-perf-summary`
  - `strict_gate_perf_summary.py`

5. Script unit tests: `src/yuantus/meta_engine/tests/test_strict_gate_perf_summary_script.py`
- Validates markdown table generation from fixture metrics JSON.
- Validates graceful output when no metrics are available.

## Verification

1. Script unit + strict-gate contracts
```bash
.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_strict_gate_perf_summary_script.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py
```
Result: `7 passed`.

2. Local smoke output (no perf metrics case)
```bash
python3 scripts/strict_gate_perf_summary.py \
  --logs-dir tmp/strict-gate/STRICT_GATE_SMOKE_LOCAL \
  --out tmp/strict-gate/STRICT_GATE_SMOKE_LOCAL/STRICT_GATE_SMOKE_LOCAL_PERF.md
```
Result: file generated with `No perf metrics found ...` note.
