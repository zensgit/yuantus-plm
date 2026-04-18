# DEV AND VERIFICATION: P2 Observation Workflow Wrapper (2026-04-18)

## Goal

Fill the last operator gap between the existing P2 observation GitHub Actions workflow and day-to-day usage by adding one local wrapper for:

1. `gh workflow run`
2. `gh run list`
3. `gh run watch`
4. `gh run download`

At the same time, reduce entry drift across the P2 observation docs so operators no longer have to choose between multiple partially-overlapping command paths.

## Implementation

### 1. New workflow wrapper

Added:

- `scripts/run_p2_observation_regression_workflow.sh`

Behavior:

- requires `gh auth status`
- dispatches `p2-observation-regression`
- polls for the new `workflow_dispatch` run id
- waits for completion
- downloads artifact `p2-observation-regression`
- writes:
  - `WORKFLOW_DISPATCH_RESULT.md`
  - `workflow_dispatch.json`

Failure behavior:

- still writes summary files on discovery failure
- still writes summary files on workflow failure after `gh run watch`
- returns non-zero when the workflow conclusion is not `success`

### 2. Tests

Added:

- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py`

Coverage:

- fake-`gh` success path
- fake-`gh` discovery failure path
- summary artifact presence
- dispatch field forwarding

Extended:

- `src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py`
- `src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py`

### 3. Docs convergence

Updated:

- `docs/P2_ONE_PAGE_DEV_GUIDE.md`
- `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`
- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
- `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
- `scripts/print_p2_shared_dev_observation_commands.sh`
- `README.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`

Net effect:

- shell path now points to `scripts/run_p2_observation_regression.sh`
- workflow path now points to `scripts/run_p2_observation_regression_workflow.sh`
- raw `verify + render` remains documented only as a lower-level debugging path
- P2 observation docs are now visible from `README.md` Runbooks and the scripts index

## Verification

### Commands

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_wrapper.py \
  src/yuantus/meta_engine/tests/test_p2_observation_regression_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

### Expected outcome

- new workflow wrapper tests pass
- shell help/syntax contracts pass
- workflow dispatch doc contract still passes
- README runbook reference/sorting contracts pass
- delivery doc index completeness/sorting contracts pass

## Scope Boundary

This slice does **not** change P2 observation business logic, API behavior, dashboard semantics, or workflow YAML semantics.

It only improves:

- operator entry consistency
- workflow invocation repeatability
- documentation discoverability
- contract coverage for the new wrapper surface
