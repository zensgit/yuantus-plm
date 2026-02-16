# DEVLOG 2026-02-16: strict-gate weekly perf-smoke schedule

## Scope

Continue strict-gate hardening by adding a weekly scheduled perf-smoke run while preserving current default behavior (daily core strict-gate without perf-smokes).

## Changes

1. `.github/workflows/strict-gate.yml`
- Added second schedule trigger:
  - daily core run: `0 3 * * *`
  - weekly perf run: `0 4 * * 1` (Monday 04:00 UTC)
- Perf-smoke env exports now happen in two cases:
  - manual dispatch with `run_perf_smokes=true`
  - weekly scheduled cron (`github.event.schedule == "0 4 * * 1"`)
- Extended job summary hints with trigger/mode metadata:
  - trigger type
  - demo/perf toggles
  - mode reason (`default` / `workflow_dispatch` / `weekly_schedule_perf`)

2. `docs/RUNBOOK_STRICT_GATE.md`
- Updated trigger section to document both schedules and semantics:
  - daily core strict-gate (no perf by default)
  - weekly scheduled perf-smoke run

3. `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`
- Added contract assertions for:
  - weekly cron line
  - `github.event.schedule` wiring
  - `weekly_schedule_perf` marker in workflow script block
  - runbook weekly schedule token

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
rg -n "0 3 \\* \\* \\*|0 4 \\* \\* 1|run_perf_smokes|weekly_schedule_perf|github.event.schedule" \
  .github/workflows/strict-gate.yml \
  docs/RUNBOOK_STRICT_GATE.md \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py
```
Result: all expected tokens present.

## Notes

- This change keeps the “default no-perf” behavior intact for daily and default manual runs.
- Perf-smokes now have a built-in weekly CI cadence without requiring manual dispatch.
