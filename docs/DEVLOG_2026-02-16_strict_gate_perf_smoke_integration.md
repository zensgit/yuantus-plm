# DEVLOG 2026-02-16: strict-gate perf smoke integration

## Scope

Integrate the three newly added perf-smoke scripts into strict-gate report flow as optional steps, and freeze the wiring with CI contracts.

## Changes

1. `scripts/strict_gate_report.sh`
- Added optional env toggles:
  - `RUN_RELEASE_ORCH_PERF=1`
  - `RUN_ESIGN_PERF=1`
  - `RUN_REPORTS_PERF=1`
- Added three optional step executions:
  - `verify_release_orchestration_perf_smoke`
  - `verify_esign_perf_smoke`
  - `verify_reports_perf_smoke`
- Added status/duration/log tracking for each perf step.
- Included perf steps in overall PASS/FAIL aggregation.
- Added perf rows in report `## Results` table.
- Added perf toggles in report `## Notes`.
- Added perf sections in `## Failure Tails`.
- Updated `--help` environment docs and examples.

2. `docs/RUNBOOK_STRICT_GATE.md`
- Documented three new optional strict-gate perf-smoke steps and their env toggles.
- Added a local run example to enable all three perf smokes.
- Added triage guidance for `verify_*_perf_smoke` failures.

3. CI contract tests
- Added `src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py`:
  - asserts perf toggles are documented in script text/help/notes
  - asserts perf wiring exists in status/log/result/failure-tail sections
- Updated `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`:
  - runbook contract now requires perf-smoke commands/toggles to remain documented.

## Verification

1. Shell syntax + help tokens
```bash
bash -n scripts/strict_gate_report.sh
bash scripts/strict_gate_report.sh --help | rg -n "RUN_RELEASE_ORCH_PERF|RUN_ESIGN_PERF|RUN_REPORTS_PERF|strict_gate_report.sh"
```
Result: pass.

2. Targeted CI-contract test set
```bash
.venv/bin/pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_perf_smokes.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```
Result: `8 passed`.

3. Lightweight local strict-gate smoke (without heavy pytest/playwright/perf execution)
```bash
RUN_ID=STRICT_GATE_SMOKE_LOCAL \
OUT_DIR=tmp/strict-gate/STRICT_GATE_SMOKE_LOCAL \
REPORT_PATH=tmp/strict-gate/STRICT_GATE_SMOKE_LOCAL/STRICT_GATE_SMOKE_LOCAL.md \
PYTEST_BIN=/usr/bin/true \
PLAYWRIGHT_CMD=true \
TARGETED_PYTEST_ARGS='smoke' \
bash scripts/strict_gate_report.sh
```
Result: `STRICT_GATE_REPORT: PASS`.

4. Confirm report content includes new perf rows/notes
```bash
rg -n "verify_release_orchestration_perf_smoke|verify_esign_perf_smoke|verify_reports_perf_smoke|RUN_RELEASE_ORCH_PERF|RUN_ESIGN_PERF|RUN_REPORTS_PERF" \
  tmp/strict-gate/STRICT_GATE_SMOKE_LOCAL/STRICT_GATE_SMOKE_LOCAL.md
```
Result: pass (rows + notes present, default `SKIP` when env toggles unset).

## Notes

- CI workflow `.github/workflows/strict-gate.yml` was intentionally not changed in this patch; perf-smoke steps stay optional and opt-in via env toggles.
