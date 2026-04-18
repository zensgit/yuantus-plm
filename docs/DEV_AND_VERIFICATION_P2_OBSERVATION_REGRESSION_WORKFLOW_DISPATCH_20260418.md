# DEV AND VERIFICATION - P2 Observation Regression Workflow Dispatch - 2026-04-18

## Goal

Add a fixed GitHub Actions entrypoint for P2 observation regression without coupling it to `strict-gate` or `release_orchestration`.

## Delivered

- `.github/workflows/p2-observation-regression.yml`
- `scripts/run_p2_observation_regression.sh`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_wrapper_login.py`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`

## Design

This implementation takes the minimal fixed-entry shape:

1. dedicated `workflow_dispatch` workflow
2. wrapper-level login support when `TOKEN` is absent
3. current-only evaluation in workflow
4. artifact upload for observation evidence

It intentionally does **not** inject P2 observation into `strict-gate` and does **not** reuse `release_orchestration`.

## Verification

### 1. Focused P2 workflow + wrapper tests

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_wrapper_login.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py
```

Observed:

- `6 passed`

### 2. Workflow / docs contracts

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_workflow_script_reference_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_manual_dispatch_presence_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_dispatch_inputs_metadata_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_dispatch_input_name_style_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_dispatch_input_default_type_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_dispatch_input_type_allowlist_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Observed:

- `24 passed`

### 3. Broad workflow contract sweep

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_workflow_*contracts.py
```

Observed:

- first run exposed 2 workflow artifact contract gaps:
  - upload step must declare `if: always()`
  - upload step must declare `retention-days`
- after remediation: `43 passed`

## Outcome

P2 observation regression now has a fixed CI-facing manual entry:

- workflow dispatch
- shell wrapper
- renderer/evaluator artifacts
- uploadable evidence bundle

That is the right next step before deciding whether this path ever belongs in a heavier gate.
