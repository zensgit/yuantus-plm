# DEV AND VERIFICATION - P2 Observation Regression Workflow Precheck Closeout - 2026-04-18

## Goal

Harden the `p2-observation-regression` workflow so missing secrets no longer produce an opaque Actions failure with no operator-facing evidence.

This follow-up was necessary because repo-side execution prerequisites are not yet fully present:

- `gh auth status` is healthy
- workflow `p2-observation-regression` is registered and active
- repo secret list does not currently expose `P2_OBSERVATION_TOKEN` / `P2_OBSERVATION_PASSWORD`

## Delivered

- `.github/workflows/p2-observation-regression.yml`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`

## What Changed

### 1. Precheck evidence on missing auth

The workflow now writes:

- `WORKFLOW_PRECHECK.md`
- `workflow_precheck.json`

when neither `P2_OBSERVATION_TOKEN` nor `P2_OBSERVATION_PASSWORD` is configured.

### 2. Summary and artifact still run on failure

The workflow now:

- runs the summary step under `if: always()`
- uploads the artifact under `if: always()`
- fails only in the final gate step

This keeps failure semantics strict while preserving operator evidence.

### 3. Explicit final gate

The last workflow step now fails the run when:

- auth precheck failed, or
- observation execution failed

That prevents accidental green runs while still keeping summary/artifact output available.

## Verification

### 1. Focused workflow contract

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py
```

Observed:

- `1 passed`

### 2. Targeted observation workflow surface

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_wrapper_login.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_regression_evaluator.py \
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

- `32 passed`

### 3. Broad workflow contract sweep

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_workflow_*contracts.py
```

Observed:

- `43 passed`

## Outcome

The workflow remains manual-only and environment-dependent, but it no longer fails opaquely when repo secrets are missing.

Operators now get:

1. an explicit precheck artifact
2. a job summary with the failure reason
3. a final red workflow status only after evidence is preserved
