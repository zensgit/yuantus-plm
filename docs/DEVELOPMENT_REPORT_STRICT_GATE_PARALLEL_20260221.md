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

## Workflow Inline Shell Syntax Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added a contract test that loads all `.github/workflows/*.yml`.
  - For each inline `run:` step in ubuntu jobs:
    - normalizes GitHub expressions (`${{ ... }}`) to placeholders
    - runs `bash -n` on the normalized script
  - This catches inline shell syntax regressions before remote Actions execution.

- Local validation:
  - strict-gate/contracts/doc-index focused suite + inline syntax contract
  - Result: `24 passed`
- Remote validation:
  - CI run `22308245213` (`main@786b357`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`

## Playwright E-sign Retry Hardening

- Changed files:
  - `.github/workflows/ci.yml`
  - `src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py` (new)

- Key updates:
  - `playwright-esign` job `Playwright e-sign smoke` step now uses bounded retry:
    - attempts: `2`
    - retry delay: `5s`
    - final explicit failure message after retries exhausted
  - Added CI contract test to lock retry behavior tokens and prevent accidental removal.

- Local validation:
  - strict-gate/contracts/doc-index focused suite + new playwright retry contract
  - Result: `25 passed`

## Workflow Script Reference Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added a workflow contract that scans:
    - inline `run:` commands using `bash|python|python3 scripts/...`
    - explicit workflow `on.*.paths` entries under `scripts/*.sh|*.py`
  - Enforces referenced script files exist in repository.
  - Runs `bash -n` over all workflow-referenced local shell scripts.
  - Runs `py_compile` over all workflow-referenced local python scripts.
  - Kept matching scoped to interpreter-based invocations to avoid false positives for external checkouts (for example `cd CADGameFusion && ./scripts/...`).

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
  - Result: `10 passed`
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `28 passed`
- Remote validation:
  - CI run `22308729532` (`main@e992f60`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - CI run `22308784174` (`main@7015780`) `success`
  - CI run `22310525549` (`main@1982de7`) `success`

## Workflow Trigger Paths Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)
  - `.github/workflows/perf-roadmap-9-3.yml` (fixed stale trigger path)

- Key updates:
  - Added workflow trigger-path contract:
    - scans `on.*.paths` / `on.*.paths-ignore`
    - for non-glob literal paths, asserts target exists in repository
    - for glob paths, asserts at least one repository target is matched
  - New guard immediately found a stale path in `perf-roadmap-9-3` trigger list:
    - from `src/yuantus/settings.py` (missing)
    - to `src/yuantus/config/settings.py` (existing)

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `30 passed`
- Remote validation:
  - CI run `22310652454` (`main@4708ebe`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`

## Workflow Schedule Cron Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added repository-level schedule cron contract:
    - scans workflow `on.schedule[].cron` entries
    - validates 5-field numeric cron syntax (`*`, list, range, step)
    - validates field ranges (minute/hour/dom/month/dow)
    - rejects duplicate cron expressions within the same workflow

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `31 passed`

- Remote validation:
  - CI run `22312847347` (`main@22d0d53`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`

## Workflow Uses Ref Pinning Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow `uses` ref pinning contract:
    - scans all workflow `uses:` entries
    - requires pinning to version tags (`vX`, `vX.Y`, `vX.Y.Z`) or 40-char commit SHA
    - allows local actions (`./...`) and `docker://...`
    - rejects floating refs (`main`, `master`, `latest`, `head`)

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `32 passed`

- Remote validation:
  - CI run `22312923023` (`main@33d6b7d`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`

## Workflow Permissions Policy Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)
  - `.github/workflows/regression.yml` (add explicit minimal permissions)
  - `.github/workflows/strict-gate.yml` (add explicit minimal permissions)

- Key updates:
  - Added workflow permissions contract:
    - forbids broad presets (`permissions: write-all` / `read-all`)
    - requires permission values in `{read, write, none}`
    - requires top-level workflow `permissions` mapping for all workflows
    - requires both `contents` and `actions` scopes in the mapping
    - requires `actions: write` when workflow performs Actions-mutating operations (dispatch/rerun)
    - requires explicit permissions for workflows exposing `${{ github.token }}` to `GH_TOKEN` / `GITHUB_TOKEN`
  - Hardened workflows to avoid implicit token defaults:
    - `ci`: `contents: read`, `actions: read`
    - `regression`: `contents: read`, `actions: read`
    - `strict-gate`: `contents: read`, `actions: read`
  - Initial hardening was applied to `strict-gate`; this round completed explicit-baseline coverage for `ci` and `regression`.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `33 passed`

- Remote validation:
  - CI run `22337410927` (`main@37a5cf8`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - CI run `22337960488` (`main@a98c284`) `success`

## Workflow Artifact Retention Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)
  - `.github/workflows/perf-p5-reports.yml` (artifact retention added)
  - `.github/workflows/perf-roadmap-9-3.yml` (artifact retention added)
  - `.github/workflows/regression.yml` (artifact retention added)
  - `.github/workflows/strict-gate-recent-perf-regression.yml` (artifact retention added)
  - `.github/workflows/strict-gate.yml` (artifact retention added)

- Key updates:
  - Added upload-artifact retention contract:
    - scans all `actions/upload-artifact@v4` steps
    - requires `with.retention-days`
    - constrains retention to integer `[1, 30]`
  - Standardized repository artifact retention to `14` days across all current upload-artifact steps.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `34 passed`

- Remote validation:
  - CI run `22338842810` (`main@602674a`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`

## Workflow Job Timeout Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated; missing timeout-minutes added)
  - `.github/workflows/regression.yml` (missing timeout-minutes added)

- Key updates:
  - Added workflow job timeout contract:
    - scans all workflow jobs under `.github/workflows/*.yml`
    - requires `timeout-minutes` on each job
    - constrains timeout to integer range `[1, 120]`
  - Hardened workflows with explicit bounded timeouts for previously uncovered jobs:
    - `ci.detect_changes_ci`: `10`
    - `ci.contracts`: `20`
    - `ci.plugin-tests`: `30`
    - `ci.playwright-esign`: `30`
    - `regression.detect_changes_regression`: `10`

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `35 passed`

- Remote validation:
  - CI run `22339012501` (`main@70b2bed`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22339012511` (`main@70b2bed`) `success`

## Workflow Runner Policy Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow runner policy contract:
    - scans all workflow jobs under `.github/workflows/*.yml`
    - requires each job to declare `runs-on`
    - constrains `runs-on` to an allowlist (`ubuntu-latest`)
  - This blocks accidental drift to unvetted runner labels and keeps CI execution environment predictable.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `36 passed`

- Remote validation:
  - CI run `22339862634` (`main@64f0797`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22339862640` (`main@64f0797`) `success`

## Workflow Upload Artifact Name Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added upload-artifact naming contract:
    - scans all `actions/upload-artifact@v4` steps in `.github/workflows/*.yml`
    - requires non-empty `with.name` for each upload step
    - requires artifact names to be unique per workflow file
  - This prevents artifact overwrite/ambiguity and keeps downstream artifact indexing stable.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `37 passed`

- Remote validation:
  - CI run `22341220054` (`main@d2925bf`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22341220056` (`main@d2925bf`) `success`

## Workflow Permissions Least Privilege Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow least-privilege permissions contract:
    - requires `permissions.contents == read` for all workflows
    - requires `permissions.actions == read` for all workflows by default
    - allows `permissions.actions == write` only for explicit allowlist workflows
  - Current allowlist:
    - `strict-gate-recent-perf-regression.yml` (needs Actions write to run strict-gate dispatch/rerun flows)

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `38 passed`

- Remote validation:
  - CI run `22341315560` (`main@7acc1b3`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22341315534` (`main@7acc1b3`) `success`

## Workflow Concurrency Baseline Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added all-workflows concurrency contract:
    - scans all `.github/workflows/*.yml`
    - requires top-level `concurrency` mapping
    - requires `concurrency.group` to include both `github.workflow` and `github.ref`
    - requires `concurrency.cancel-in-progress: true`
  - This upgrades concurrency checks from key-workflow coverage to full workflow coverage.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `39 passed`

- Remote validation:
  - CI run `22343593550` (`main@9304bf0`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22343593571` (`main@9304bf0`) `success`

## Workflow Dispatch Input Typing Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)
  - `.github/workflows/regression.yml` (workflow_dispatch input type normalized)

- Key updates:
  - Added workflow_dispatch inputs contract:
    - scans all `.github/workflows/*.yml`
    - for workflows declaring `workflow_dispatch.inputs`, requires each input to define explicit `type`
    - constrains input type to allowed set: `string|boolean|choice|number|environment`
  - Hardened `regression.yml` dispatch schema:
    - `run_cad_ml` now declares `type: string` explicitly.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `40 passed`

- Remote validation:
  - CI run `22343717312` (`main@6398ede`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22343717293` (`main@6398ede`) `success`

## Workflow Job Naming Baseline Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated; job names added)
  - `.github/workflows/perf-p5-reports.yml` (job name added)
  - `.github/workflows/perf-roadmap-9-3.yml` (job name added)
  - `.github/workflows/regression.yml` (job names added)
  - `.github/workflows/strict-gate-recent-perf-regression.yml` (job name added)
  - `.github/workflows/strict-gate.yml` (job name added)

- Key updates:
  - Added all-workflows job naming contract:
    - scans all `.github/workflows/*.yml`
    - requires every workflow job to define a non-empty string `name`
  - Hardened uncovered jobs with explicit display names in CI/perf/regression/strict-gate workflows.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `41 passed`

- Remote validation:
  - CI run `22343978622` (`main@f16ae59`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22343978637` (`main@f16ae59`) `success`

## Workflow Name Uniqueness Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow name uniqueness contract:
    - scans all `.github/workflows/*.yml`
    - requires top-level `name` to be a non-empty string
    - requires workflow names to be globally unique (case-insensitive, whitespace-normalized)
  - This prevents duplicate workflow labels in Actions UI and keeps run indexing unambiguous.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `42 passed`

- Remote validation:
  - CI run `22344227383` (`main@f63187d`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22344227379` (`main@f63187d`) `success`

## Workflow Needs Graph Integrity Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow needs integrity contract:
    - scans all `.github/workflows/*.yml`
    - validates each `needs` target resolves to an existing job id
    - rejects self-dependency and duplicate dependency entries
    - enforces acyclic job dependency graph
  - This catches broken DAG wiring early and prevents runtime scheduling errors.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `43 passed`

- Remote validation:
  - CI run `22344358959` (`main@706daac`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22344358947` (`main@706daac`) `success`

## Workflow Dispatch Input Metadata Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow_dispatch metadata contract:
    - scans all `.github/workflows/*.yml`
    - requires each `workflow_dispatch.inputs.*` to declare non-empty `description`
    - requires explicit boolean `required`
    - requires optional inputs (`required: false`) to declare `default`
    - for `type: choice`, requires non-empty unique string `options`
    - for `type: choice`, requires `default` (if present) to be one of `options`
  - This reduces dispatch UI/parameter drift and keeps manual trigger semantics stable.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `44 passed`

- Remote validation:
  - CI run `22344532805` (`main@799f60e`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22344532766` (`main@799f60e`) `success`

## Workflow No Job-Level Permissions Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added no-job-level-permissions contract:
    - scans all `.github/workflows/*.yml`
    - requires each workflow job not to declare `permissions`
    - enforces permission control at workflow top-level only
  - This prevents accidental per-job privilege overrides and keeps least-privilege policy centralized.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `45 passed`

- Remote validation:
  - CI run `22344674163` (`main@bc3938d`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22344674187` (`main@bc3938d`) `success`

## Workflow Permissions Scope Allowlist Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added permissions scope allowlist contract:
    - scans all `.github/workflows/*.yml`
    - requires top-level `permissions` scopes to stay within allowlist
    - current allowlist: `actions`, `contents`
  - This prevents silent introduction of additional token scopes and keeps permission surface area explicit.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `46 passed`

- Remote validation:
  - CI run `22345076941` (`main@cc4f35b`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22345076968` (`main@cc4f35b`) `success`

## Workflow Trigger Event Allowlist Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow trigger event allowlist contract:
    - scans all `.github/workflows/*.yml`
    - enforces top-level `on` mapping to use only allowlisted events
    - current allowlist: `pull_request`, `push`, `schedule`, `workflow_dispatch`
  - This prevents accidental introduction of noisy/unreviewed trigger types.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `47 passed`

- Remote validation:
  - CI run `22345216672` (`main@7e83820`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22345216600` (`main@7e83820`) `success`

## Workflow Concurrency Group Template Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added strict concurrency group template contract:
    - scans all `.github/workflows/*.yml`
    - enforces `concurrency.group == '${{ github.workflow }}-${{ github.ref }}'`
    - enforces `concurrency.cancel-in-progress == true`
  - This upgrades baseline from loose token-inclusion checks to exact template consistency.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `48 passed`

- Remote validation:
  - CI run `22346129335` (`main@62d659c`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22346129313` (`main@62d659c`) `success`

## Workflow Dispatch Default Type Consistency Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow_dispatch default type contract:
    - scans all `.github/workflows/*.yml`
    - for inputs with `default`, enforces default type matches declared `type`
    - enforced mappings:
      - `boolean -> bool`
      - `string|choice|environment -> str`
      - `number -> numeric`
  - This prevents subtle dispatch-input coercion drift between UI and scripts.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `49 passed`

- Remote validation:
  - CI run `22346265112` (`main@655aebc`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22346265111` (`main@655aebc`) `success`

## Workflow Upload Artifact Missing-File Policy Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_upload_artifact_if_no_files_found_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)
  - `.github/workflows/perf-p5-reports.yml` (upload steps normalized)
  - `.github/workflows/perf-roadmap-9-3.yml` (upload steps normalized)
  - `.github/workflows/regression.yml` (upload steps normalized)
  - `.github/workflows/strict-gate-recent-perf-regression.yml` (upload steps normalized)
  - `.github/workflows/strict-gate.yml` (upload steps normalized)

- Key updates:
  - Added upload-artifact missing-file policy contract:
    - scans all `.github/workflows/*.yml`
    - checks each `actions/upload-artifact@...` step
    - requires explicit `with.if-no-files-found`
    - allowed values: `warn|error|ignore`
  - Normalized all current upload-artifact steps to explicit policy (using `warn` where previously implicit).

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_upload_artifact_if_no_files_found_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `50 passed`

- Remote validation:
  - CI run `22348682522` (`main@ab1c7b6`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22348682527` (`main@ab1c7b6`) `success`

## Workflow Setup Runtime Version Baseline Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_setup_runtime_versions_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added runtime setup version baseline contract:
    - scans all `.github/workflows/*.yml` steps
    - enforces `actions/setup-python@v5` uses `python-version: "3.11"`
    - enforces `actions/setup-node@v4` uses `node-version: "20"`
  - This prevents silent toolchain drift across CI workflows.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_setup_runtime_versions_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_if_no_files_found_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `51 passed`

- Remote validation:
  - CI run `22354343942` (`main@6e3a35b`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22354343997` (`main@6e3a35b`) `success`

## Workflow Manual Dispatch Presence Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_manual_dispatch_presence_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added manual dispatch presence contract:
    - scans all `.github/workflows/*.yml`
    - requires `on.workflow_dispatch` on every workflow
    - requires `workflow_dispatch` to be a mapping (use `{}` when no inputs)
  - This keeps all workflows manually operable for on-demand validation and incident recovery.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_manual_dispatch_presence_contracts.py src/yuantus/meta_engine/tests/test_workflow_setup_runtime_versions_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_if_no_files_found_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `52 passed`

- Remote validation:
  - CI run `22383963324` (`main@8bad22e`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22383963293` (`main@8bad22e`) `success`

## Workflow Dispatch Input Naming Style Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_dispatch_input_name_style_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow_dispatch input naming style contract:
    - scans all `.github/workflows/*.yml`
    - for `workflow_dispatch.inputs`, enforces snake_case pattern `^[a-z][a-z0-9_]*$`
    - rejects consecutive underscores (`__`) in input names
  - This stabilizes dispatch input IDs for downstream script and docs references.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_dispatch_input_name_style_contracts.py src/yuantus/meta_engine/tests/test_workflow_manual_dispatch_presence_contracts.py src/yuantus/meta_engine/tests/test_workflow_setup_runtime_versions_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_if_no_files_found_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `53 passed`

- Remote validation:
  - CI run `22388541034` (`main@9abadd4`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22388541012` (`main@9abadd4`) `success`

## Workflow Upload Artifact Always Condition Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_upload_artifact_always_condition_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added upload-artifact always-condition contract:
    - scans all `.github/workflows/*.yml`
    - for each `actions/upload-artifact@...` step, requires non-empty `if`
    - requires `if` condition to include `always()`
  - This guarantees artifact publishing remains available on failure paths.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_upload_artifact_always_condition_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_name_style_contracts.py src/yuantus/meta_engine/tests/test_workflow_manual_dispatch_presence_contracts.py src/yuantus/meta_engine/tests/test_workflow_setup_runtime_versions_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_if_no_files_found_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `54 passed`

- Remote validation:
  - CI run `22391639269` (`main@8a14fb2`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22391639281` (`main@8a14fb2`) `success`

## Workflow Git Diff Fetch-Depth Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_git_diff_fetch_depth_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added git-diff checkout depth contract:
    - scans all `.github/workflows/*.yml` jobs
    - identifies jobs with inline `git diff` usage
    - requires those jobs to include `actions/checkout@...` with `with.fetch-depth: 0`
  - This prevents shallow-clone history gaps from breaking change-scope detection.

- Local validation:
  - `pytest -q src/yuantus/meta_engine/tests/test_workflow_git_diff_fetch_depth_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_always_condition_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_name_style_contracts.py src/yuantus/meta_engine/tests/test_workflow_manual_dispatch_presence_contracts.py src/yuantus/meta_engine/tests/test_workflow_setup_runtime_versions_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_if_no_files_found_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_event_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_scope_allowlist_contracts.py src/yuantus/meta_engine/tests/test_workflow_no_job_level_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py src/yuantus/meta_engine/tests/test_workflow_needs_integrity_contracts.py src/yuantus/meta_engine/tests/test_workflow_name_uniqueness_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_name_contracts.py src/yuantus/meta_engine/tests/test_workflow_runner_policy_contracts.py src/yuantus/meta_engine/tests/test_workflow_job_timeout_contracts.py src/yuantus/meta_engine/tests/test_workflow_upload_artifact_retention_contracts.py src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py src/yuantus/meta_engine/tests/test_workflow_action_uses_refs_contracts.py src/yuantus/meta_engine/tests/test_workflow_schedule_cron_contracts.py src/yuantus/meta_engine/tests/test_workflow_trigger_paths_contracts.py src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_playwright_esign_retry.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py src/yuantus/meta_engine/tests/test_workflow_yaml_parseability_contracts.py src/yuantus/meta_engine/tests/test_workflow_inline_shell_syntax_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_regression_workflow_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_recent_perf_audit_regression_script_behavior_contracts.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py src/yuantus/meta_engine/tests/test_strict_gate_workflow_dispatch_input_type_contracts.py src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_strict_gate_report_perf_smokes.py src/yuantus/meta_engine/tests/test_readme_runbook_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py src/yuantus/meta_engine/tests/test_runbook_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: `55 passed`

- Remote validation:
  - CI run `22394016044` (`main@7f2bea7`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22394016027` (`main@7f2bea7`) `success`

## Workflow Push Branch Allowlist Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_push_branch_allowlist_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added push-branch allowlist contract:
    - scans all `.github/workflows/*.yml`
    - for workflows that declare `on.push`, requires explicit `on.push.branches`
    - enforces branch values to stay in allowlist `main|master`
    - requires `main` to be present
    - rejects `branches-ignore` and duplicate branch entries
  - This prevents accidental push-trigger fanout to unreviewed branches.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `139 passed, 1 skipped`

- Remote validation:
  - CI run `22396585721` (`main@b6d2bfb`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22396585745` (`main@b6d2bfb`) `success`

## Workflow Schedule Frequency Floor Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_schedule_frequency_floor_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added schedule frequency floor contract:
    - scans all `.github/workflows/*.yml`
    - extracts every `on.schedule[].cron` expression
    - enforces cron minute field to be a fixed numeric literal (`0-59`)
    - rejects wildcard/list/range/step minute forms that can produce minute-level cadence
  - This keeps scheduled workflows at hourly-or-slower cadence and prevents accidental high-frequency trigger spikes.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `140 passed, 1 skipped`

- Remote validation:
  - CI run `22401346569` (`main@f9f26e0`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22401346562` (`main@f9f26e0`) `success`

## Workflow Dispatch Input Type Allowlist Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_dispatch_input_type_allowlist_contracts.py` (new)
  - `.github/workflows/ci.yml` (contracts list updated)

- Key updates:
  - Added workflow_dispatch input type allowlist contract:
    - scans all `.github/workflows/*.yml`
    - inspects every `on.workflow_dispatch.inputs.*.type`
    - enforces allowed set: `boolean|choice|string|number|environment`
    - rejects missing/empty/unknown input types
  - This prevents unsupported dispatch input type drift and keeps trigger schema stable.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `141 passed, 1 skipped`

- Remote validation:
  - CI run `22401513387` (`main@6ec236c`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22401513408` (`main@6ec236c`) `success`

## Workflow Checkout Fetch-Depth Explicit Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_checkout_fetch_depth_contracts.py` (new)
  - `.github/workflows/ci.yml`
  - `.github/workflows/perf-p5-reports.yml`
  - `.github/workflows/perf-roadmap-9-3.yml`
  - `.github/workflows/regression.yml`
  - `.github/workflows/strict-gate-recent-perf-regression.yml`
  - `.github/workflows/strict-gate.yml`

- Key updates:
  - Added checkout fetch-depth explicit contract:
    - scans all `.github/workflows/*.yml` jobs/steps
    - checks every `actions/checkout@...` step
    - requires `with.fetch-depth` to be explicitly declared
    - enforces bounded values: `0|1`
  - Normalized all workflow checkout steps to explicit depth declarations.
  - This removes implicit checkout defaults and stabilizes clone behavior across workflows.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `142 passed, 1 skipped`

- Remote validation:
  - CI run `22402324193` (`main@ea69051`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22402324107` (`main@ea69051`) `success`

## Workflow External Checkout Ref Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_checkout_external_ref_contracts.py` (new)
  - `.github/workflows/ci.yml`
  - `.github/workflows/regression.yml`

- Key updates:
  - Added external checkout ref contract:
    - scans all `.github/workflows/*.yml` jobs/steps
    - checks `actions/checkout@...` steps with `with.repository`
    - requires explicit non-empty `with.ref`
  - Normalized current external checkout steps in `regression.yml` to `ref: main`.
  - This removes implicit default-branch dependency for cross-repo checkouts.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `143 passed, 1 skipped`

- Remote validation:
  - CI run `22426651591` (`main@5e00eb4`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22426651584` (`main@5e00eb4`) `success`

## Workflow External Checkout Path Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_checkout_external_path_contracts.py` (new)
  - `.github/workflows/ci.yml`

- Key updates:
  - Added external checkout path contract:
    - scans all `.github/workflows/*.yml` jobs/steps
    - checks `actions/checkout@...` steps with `with.repository`
    - requires explicit string `with.path`
    - requires path to be safe relative path (non-empty, non-absolute, no `.`/`..` segments)
  - This prevents external repositories from being checked out into ambiguous or unsafe workspace locations.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `144 passed, 1 skipped`

- Remote validation:
  - CI run `22426785372` (`main@9adf8ce`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22426785368` (`main@9adf8ce`) `success`

## Workflow External Checkout Repository Allowlist Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_checkout_external_repository_allowlist_contracts.py` (new)
  - `.github/workflows/ci.yml`

- Key updates:
  - Added external checkout repository allowlist contract:
    - scans all `.github/workflows/*.yml` jobs/steps
    - checks `actions/checkout@...` steps with `with.repository`
    - enforces repository to stay in explicit allowlist:
      - `zensgit/cad-ml-platform`
      - `zensgit/CADGameFusion`
  - This prevents accidental introduction of unreviewed third-party checkout sources in workflows.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `145 passed, 1 skipped`

- Remote validation:
  - CI run `22486418887` (`main@7eae094`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22486418877` (`main@7eae094`) `success`

## Workflow Checkout Version Baseline Guard

- Changed files:
  - `src/yuantus/meta_engine/tests/test_workflow_checkout_version_baseline_contracts.py` (new)
  - `.github/workflows/ci.yml`

- Key updates:
  - Added checkout version baseline contract:
    - scans all `.github/workflows/*.yml` jobs/steps
    - checks each `actions/checkout@...` step
    - enforces `uses` to start with `actions/checkout@v4`
  - This prevents silent drift to older checkout action majors.

- Local validation:
  - `python3 - <<'PY' ... subprocess.run(['pytest', '-q', *paths], check=True) ... PY` (extracts contracts test list from `.github/workflows/ci.yml` and executes it)
  - Result: `146 passed, 1 skipped`

- Remote validation:
  - CI run `22486532864` (`main@8030f8e`) `success`
  - contracts job `Contract checks (perf workflows + delivery doc index)` `success`
  - regression run `22486532849` (`main@8030f8e`) `success`
