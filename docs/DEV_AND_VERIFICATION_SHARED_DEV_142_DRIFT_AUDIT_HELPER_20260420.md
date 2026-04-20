# DEV AND VERIFICATION - SHARED DEV 142 DRIFT AUDIT HELPER - 2026-04-20

## Background

- `shared-dev-142-readonly-guard` 已经能在默认分支上真实执行。
- 当前 guard 的失败已经不是 workflow wiring 问题，而是 `142` 相对 frozen readonly baseline 发生了真实漂移。
- 现有 repo 已经有：
  - readonly rerun
  - workflow probe
  - workflow readonly check
  - readonly refreeze 文档
- 但缺一条固定的 **drift triage** 入口。

## Changes

- Added `scripts/render_p2_shared_dev_142_drift_audit.py`
  - consumes baseline/current observation result dirs
  - writes:
    - `DRIFT_AUDIT.md`
    - `drift_audit.json`
  - compares:
    - summary counts
    - item count
    - export counts
    - anomaly counts
    - approval id add/remove sets
- Added `scripts/run_p2_shared_dev_142_drift_audit.sh`
  - runs the existing fixed readonly rerun into `<OUTPUT_DIR>/current`
  - renders the drift audit at the top level
- Added `scripts/print_p2_shared_dev_142_drift_audit_commands.sh`
- Extended `scripts/run_p2_shared_dev_142_entrypoint.sh`
  - new modes:
    - `drift-audit`
    - `print-drift-commands`
- Added operator doc:
  - `docs/P2_SHARED_DEV_142_DRIFT_AUDIT_CHECKLIST.md`
- Updated README / runbooks / delivery indexes / selector doc so the new drift path is discoverable

## Verification

Executed from an isolated worktree rooted at current `main` plus this helper:

```bash
bash -n scripts/run_p2_shared_dev_142_drift_audit.sh
bash -n scripts/print_p2_shared_dev_142_drift_audit_commands.sh
bash -n scripts/run_p2_shared_dev_142_entrypoint.sh
python3 scripts/render_p2_shared_dev_142_drift_audit.py --help

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## Expected Outcome

- shell wrappers are syntax-valid
- entrypoint exposes `drift-audit` and `print-drift-commands`
- drift audit renderer writes stable markdown/json outputs from fixture dirs
- discoverability/index contracts remain green

## Scope Boundary

- This helper does not auto-refreeze any baseline
- This helper does not change the official readonly baseline label
- It only makes drift capture repeatable before an operator decides whether to investigate further or refreeze
