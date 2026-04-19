# DEV AND VERIFICATION: P2 Observation Discoverability Contracts (2026-04-19)

## Goal

Lock the P2 observation operator entrypoints into CI-visible contracts so the newly converged shell/workflow path cannot silently drift out of:

1. `README.md` Runbooks
2. `docs/DELIVERY_SCRIPTS_INDEX_20260202.md`
3. `docs/DELIVERY_DOC_INDEX.md`

## Why

The previous slice added the canonical workflow wrapper and converged the docs onto:

- `scripts/run_p2_observation_regression.sh`
- `scripts/run_p2_observation_regression_workflow.sh`

That made the entrypath cleaner, but discoverability was still protected mostly by generic sorting/existence tests, not by a P2-specific contract. A later doc cleanup could have removed these paths from operator-facing surfaces without tripping a focused failure.

## Implementation

### 1. New focused contract

Added:

- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`

This test now asserts:

- `README.md` Runbooks must mention:
  - `docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md`
  - `docs/P2_ONE_PAGE_DEV_GUIDE.md`
  - `docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md`
- `docs/DELIVERY_SCRIPTS_INDEX_20260202.md` must mention:
  - `verify_p2_dev_observation_startup.sh`
  - `run_p2_observation_regression.sh`
  - `run_p2_observation_regression_workflow.sh`
  - `render_p2_observation_result.py`
  - `compare_p2_observation_results.py`
  - `evaluate_p2_observation_results.py`
- `docs/DELIVERY_DOC_INDEX.md` must mention:
  - `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`
  - the three core P2 observation runbooks
  - `docs/DEV_AND_VERIFICATION_P2_OBSERVATION_WORKFLOW_WRAPPER_20260418.md`

### 2. Delivery doc index fix

Updated:

- `docs/DELIVERY_DOC_INDEX.md`

Added missing token:

- `docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md`

This closes the gap where the handoff doc existed but was not indexed in the delivery doc surface.

## Verification

### Commands

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
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

### Result

- targeted suite passed
- new discoverability contract passed
- previous workflow wrapper contract stayed green
- generic README / delivery index contracts stayed green

## Scope Boundary

This slice is contract-only plus index alignment.

It does **not** change:

- P2 workflow YAML semantics
- shell wrapper behavior
- observation API behavior
- dashboard/export/audit logic
