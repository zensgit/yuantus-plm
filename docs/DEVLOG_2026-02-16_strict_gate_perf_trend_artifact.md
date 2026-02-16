# DEVLOG 2026-02-16: strict-gate perf trend artifact

## Scope

Continue strict-gate perf evidence chain by wiring `strict_gate_perf_trend.py` into CI and shipping a dedicated trend artifact.

## Changes

1. Workflow: `.github/workflows/strict-gate.yml`
- Added `Build strict gate perf trend` step (`if: always()`):
  - runs:
    - `python3 scripts/strict_gate_perf_trend.py`
    - `--dir docs/DAILY_REPORTS`
    - `--glob 'STRICT_GATE_*_PERF.md'`
    - `--out docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>_PERF_TREND.md`
    - `--include-empty`
  - appends trend markdown to Job Summary.
- Added new artifact:
  - name: `strict-gate-perf-trend`
  - path: `docs/DAILY_REPORTS/STRICT_GATE_CI_<run_id>_PERF_TREND.md`
- Updated download hints in Job Summary to include trend artifact command/path.

2. Runbook: `docs/RUNBOOK_STRICT_GATE.md`
- Added perf trend to evidence outputs and artifact list.
- Added `gh run download ... -n strict-gate-perf-trend`.
- Documented extracted artifact path `STRICT_GATE_CI_<run_id>_PERF_TREND.md`.

3. Contracts: `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`
- Added assertions for workflow wiring:
  - trend script invocation
  - trend output env path
  - trend artifact name/path
- Added runbook contract token:
  - `strict-gate-perf-trend`

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

2. Local trend smoke
```bash
python3 scripts/strict_gate_perf_trend.py \
  --dir docs/DAILY_REPORTS \
  --out tmp/strict-gate/STRICT_GATE_PERF_TREND_LOCAL.md \
  --limit 30
```
