# DEVLOG 2026-02-16: strict-gate workflow dispatch perf toggle

## Scope

Implement both:
1. add a manual workflow input to enable perf-smokes in strict-gate CI
2. keep default behavior unchanged (perf-smokes remain off unless explicitly enabled)

## Changes

1. `.github/workflows/strict-gate.yml`
- Added `workflow_dispatch` input:
  - `run_perf_smokes` (default `"false"`)
- In `Run strict gate report` step, only when:
  - `github.event_name == workflow_dispatch`
  - and `github.event.inputs.run_perf_smokes == "true"`
  then export:
  - `RUN_RELEASE_ORCH_PERF=1`
  - `RUN_ESIGN_PERF=1`
  - `RUN_REPORTS_PERF=1`

Result: scheduled runs and default manual runs still skip perf-smokes.

2. `docs/RUNBOOK_STRICT_GATE.md`
- Updated trigger docs to include `run_perf_smokes=true`.
- Updated CLI examples:
  - default: `run_demo=false run_perf_smokes=false`
  - demo only
  - perf-smokes only

3. `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`
- Added workflow contract assertions for:
  - `run_perf_smokes` input presence
  - perf-smoke env export wiring in workflow shell block
- Added runbook contract token:
  - `run_perf_smokes=true`

## Verification

1. Targeted contracts
```bash
.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py
```
Result: `5 passed`.

2. Token cross-check
```bash
rg -n "run_perf_smokes|run_demo=true|gh workflow run strict-gate" \
  .github/workflows/strict-gate.yml docs/RUNBOOK_STRICT_GATE.md
```
Result: workflow + runbook tokens all present.
