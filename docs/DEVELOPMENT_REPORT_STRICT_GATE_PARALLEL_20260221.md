# Development Report: Strict Gate Parallel Work (2026-02-21)

## Objectives

- Implement automated regression for strict-gate recent perf audit dispatch paths.
- Expose skip reason + artifact availability in strict-gate Job Summary.
- Reduce `always()` fan-out after validation failure to avoid empty/invalid artifact uploads.

## Delivered Changes

- Workflow hardening: `.github/workflows/strict-gate.yml`
  - Added step id: `strict_gate_report`
  - Gated report-dependent steps with `steps.strict_gate_report.outcome != 'skipped'`
  - Added summary lines:
    - `Recent perf audit skipped reason`
    - `Artifact availability: report/perf-summary/perf-trend/logs=..., recent-perf-audit=...`
  - Made download hints conditional when artifacts are not generated.

- Automation script: `scripts/strict_gate_recent_perf_audit_regression.sh`
  - Automatically triggers and validates:
    - invalid case (`recent_perf_audit_limit=101`)
    - valid case (`recent_perf_audit_limit=10`)
  - Checks step conclusions and failed log signal.
  - Downloads `strict-gate-recent-perf-audit` artifact from valid case and validates JSON fields.

- Contract/tests updates:
  - `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`
  - `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`

- Runbook update:
  - `docs/RUNBOOK_STRICT_GATE.md`

## Validation

- Local:
  - `pytest` selected contract suite: `9 passed`

- Remote (via script):
  - Run `22249050374` (invalid case): expected failure + skip matrix matched.
  - Run `22249064587` (valid case): expected success matrix matched.

Detailed verification evidence is recorded in:

- `docs/VERIFICATION_RESULTS.md` (`Run STRICT-GATE-PARALLEL-AUTOMATION-AND-SKIP-REDUCTION-20260221`)

## Follow-up Hardening (Same Day)

- Script hardening: `scripts/strict_gate_recent_perf_audit_regression.sh`
  - Added invalid-case artifact assertion (`artifact_count == 0`)
  - Added valid-case full artifact set assertion:
    - `strict-gate-report`
    - `strict-gate-perf-summary`
    - `strict-gate-perf-trend`
    - `strict-gate-logs`
    - `strict-gate-recent-perf-audit`
  - Added `--summary-json <path>` and default JSON output:
    - `STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json`

- Contracts expanded:
  - Added `src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py`
  - Updated `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py` (`--summary-json` help contract)
  - Updated CI contracts list in `.github/workflows/ci.yml`
  - Updated runbook tokens in `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`

- Local regression:
  - selected suite result: `15 passed`

- Remote regression (script re-run):
  - invalid case run `22256796464`: failure + skip matrix + `artifact_count=0`
  - valid case run `22256807700`: success + full artifact set
  - output directory:
    - `tmp/strict-gate-artifacts/recent-perf-regression/20260221-202649/`

## New Workflow Automation

- Added workflow: `.github/workflows/strict-gate-recent-perf-regression.yml`
  - Triggers:
    - `workflow_dispatch` (`ref/poll_interval_sec/max_wait_sec`)
    - weekly schedule `Tue 05:00 UTC`
  - Permissions:
    - `actions: write` (required to dispatch strict-gate runs)
    - `contents: read`
  - Artifacts:
    - `strict-gate-recent-perf-regression` (MD + JSON summary)
    - `strict-gate-recent-perf-regression-raw` (full raw output directory)

- Workflow contracts and CI wiring:
  - Added: `src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py`
  - Updated: `src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py`
  - Updated CI contracts list: `.github/workflows/ci.yml`

- Runner compatibility fix:
  - `scripts/strict_gate_recent_perf_audit_regression.sh` now falls back to `grep` when `rg` is unavailable on runner.

- Verification:
  - First workflow run `22256989310` failed at script step due missing `rg`.
  - After fix commit, workflow run `22257019598` succeeded end-to-end and uploaded both expected artifacts.

## Regression Workflow Retry Controls

- Added retry/backoff controls to `.github/workflows/strict-gate-recent-perf-regression.yml`:
  - `regression_attempts` (default `2`, range `1..3`)
  - `regression_retry_delay_sec` (default `15`, non-negative integer)
- Execution model:
  - workflow runs script under `attempt-<n>/` directories
  - on success, MD/JSON are copied to root output directory for stable artifact paths
  - on repeated failures, job fails with explicit attempts message

- Validation:
  - workflow run `22257919949` succeeded with retry controls enabled
  - run log confirms attempt execution and summary outputs under `attempt-1`

## Script Behavior Test Depth Upgrade

- Added behavior-level fake-gh test:
  - `src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py`
  - The test executes `scripts/strict_gate_recent_perf_audit_regression.sh` end-to-end with a deterministic fake `gh` binary and validates:
    - invalid/valid run detection flow
    - fallback path when `rg` is unavailable
    - artifact assertions (`invalid=0`, `valid=5`)
    - MD/JSON summary outputs

- CI contracts integration:
  - Added test path into `.github/workflows/ci.yml` contracts step.

## Failure-Evidence Persistence And Stable Valid-Case Gate

- Commit: `82a6843` (`main`)
- Changed files:
  - `.github/workflows/strict-gate-recent-perf-regression.yml`
  - `scripts/strict_gate_recent_perf_audit_regression.sh`
  - `src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py`
  - `src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py`
  - `src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py`

- Key updates:
  - `strict_gate_recent_perf_audit_regression.sh`
    - Added `--success-fail-if-no-metrics true|false` (default `false`) for valid case stability.
    - Added failure-safe summary writing (`STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md/json`) with:
      - `result`
      - `failure_reason`
      - `requested_fail_if_no_metrics`
    - Added `ERR` trap to persist summary on assertion/command failures.
  - `strict-gate-recent-perf-regression.yml`
    - Writes `REGRESSION_RUN_CONTEXT.txt` at run root.
    - Copies per-attempt summary MD/JSON back to root whenever available (success or failure), avoiding empty evidence artifacts.
  - Added executable behavior test for failure path summary persistence.

- Local validation:
  - `pytest -q ...` strict-gate/recent-perf/contracts/doc-index focused suite
  - Result: `20 passed`

- Remote validation:
  - Workflow run: `22258508018` (`main@82a6843`) -> `success`
  - Link: `https://github.com/zensgit/yuantus-plm/actions/runs/22258508018`
  - Artifacts (download-verified):
    - `strict-gate-recent-perf-regression` (MD + JSON)
    - `strict-gate-recent-perf-regression-raw` (includes `REGRESSION_RUN_CONTEXT.txt`, `attempt-1/`)
  - Summary JSON key values:
    - `result: "success"`
    - `invalid_case.run_id: "22258509811"` (`failure`, `artifact_count=0`)
    - `valid_case.run_id: "22258522354"` (`success`)
    - `valid_case.requested_fail_if_no_metrics: false`
  - Failure-path proof (forced timeout inputs):
    - Workflow run: `22258609718` (`main@7ad11ea`) -> `failure`
    - Dispatch inputs: `poll_interval_sec=2`, `max_wait_sec=10`, `regression_attempts=1`, `regression_retry_delay_sec=0`
    - Both upload steps still `success`; downloadable artifacts include:
      - evidence: `STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md/json`
      - raw: `REGRESSION_RUN_CONTEXT.txt`, `attempt-1/STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md/json`
    - failure summary JSON key fields:
      - `result: "failure"`
      - `failure_reason: "timeout waiting run completion: 22258612100"`

## Dispatch Input Exposure: success_fail_if_no_metrics

- Commit: `881512d` (`main`)
- Changed files:
  - `.github/workflows/strict-gate-recent-perf-regression.yml`
  - `docs/RUNBOOK_STRICT_GATE.md`
  - `src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py`
  - `src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py`

- Key updates:
  - Regression workflow `workflow_dispatch` adds:
    - `success_fail_if_no_metrics` (default `false`)
  - Runtime validations add:
    - `success_fail_if_no_metrics must be true|false`
  - Value is:
    - recorded in `REGRESSION_RUN_CONTEXT.txt`
    - forwarded to script via `--success-fail-if-no-metrics`.
  - Runbook updated to document the new dispatch input.

- Local validation:
  - strict-gate/contracts/doc-index focused suite
  - Result: `22 passed`

- Remote validation (input wiring proof):
  - Workflow run: `22267857288` (`main@881512d`) -> `failure` (forced timeout config)
  - Dispatch inputs:
    - `poll_interval_sec=2`
    - `max_wait_sec=10`
    - `regression_attempts=1`
    - `regression_retry_delay_sec=0`
    - `success_fail_if_no_metrics=true`
  - Downloaded raw context confirms input propagation:
    - `success_fail_if_no_metrics=true`
  - Summary markdown confirms script-level view:
    - `requested recent_perf_fail_if_no_metrics: true`

## Validation-Failure Summary On Dispatch Input Errors

- Commit: `1462137` (`main`)
- Changed file:
  - `.github/workflows/strict-gate-recent-perf-regression.yml`

- Key updates:
  - In `Run strict-gate recent perf audit regression` step:
    - Added `write_validation_failure_summary` and `fail_validation` helpers.
    - Invalid dispatch inputs now generate:
      - `STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md`
      - `STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json`
    - `REGRESSION_RUN_CONTEXT.txt` is written before validation checks, preserving raw input values.
  - This removes prior “input校验失败时 evidence 为空”缺口。

- Local validation:
  - strict-gate/contracts/doc-index focused suite
  - Result: `22 passed`

- Remote validation (invalid input hard proof):
  - Workflow run: `22306786190` (`main@1462137`) -> `failure`
  - Dispatch inputs:
    - `success_fail_if_no_metrics=maybe`
    - `regression_attempts=1`
    - `regression_retry_delay_sec=0`
  - Key steps:
    - `Run strict-gate recent perf audit regression`: `failure`
    - `Upload strict-gate recent perf regression evidence`: `success`
    - `Upload strict-gate recent perf regression raw outputs`: `success`
  - Evidence verification:
    - JSON: `result="failure"`, `failure_reason="success_fail_if_no_metrics must be true|false (got: maybe)"`
    - Raw context includes: `success_fail_if_no_metrics=maybe`

## Workflow YAML Parseability Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added repository-wide workflow parseability contract:
    - Loads every `.github/workflows/*.yml` with `yaml.safe_load`.
    - Asserts core keys exist (`name`, `on` trigger, non-empty `jobs`).
    - Handles PyYAML YAML 1.1 `on -> True` behavior safely.
  - Added the new test into CI contracts step (sorted order preserved).

- Local validation:
  - strict-gate/contracts/doc-index focused suite + parseability contract
  - Result: `23 passed`
