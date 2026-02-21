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
