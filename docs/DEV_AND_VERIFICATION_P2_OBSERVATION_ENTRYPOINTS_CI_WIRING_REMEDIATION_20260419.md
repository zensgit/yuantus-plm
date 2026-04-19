# DEV_AND_VERIFICATION_P2_OBSERVATION_ENTRYPOINTS_CI_WIRING_REMEDIATION_20260419

## Objective

Close the last CI gap on PR `#250` by wiring the new P2 observation discoverability contract into `.github/workflows/ci.yml` so the remote `contracts` job executes the same guard that already passed locally.

## Root Cause

PR `#250` added:

- `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`

but the `contracts` step in `.github/workflows/ci.yml` did not include that file in its explicit pytest list.

As a result:

- local focused verification passed because it invoked the new test directly
- GitHub `contracts` failed through `test_ci_contracts_job_wiring.py`
- failure mode: the workflow itself drifted from the repo's contract inventory

## Code Changes

### 1. CI workflow wiring

Updated:

- `.github/workflows/ci.yml`

Change:

- inserted `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py` into the `Contract checks (perf workflows + delivery doc index)` pytest list
- placement kept path-sorted ordering intact so `test_ci_contracts_ci_yml_test_list_order.py` remains satisfied

### 2. Delivery indexing

Updated:

- `docs/DELIVERY_DOC_INDEX.md`

Change:

- added this remediation note to the `Development & Verification` section in sorted position

## Verification

### Reproduced failure source

Fetched failing GitHub Actions log for PR `#250`:

- workflow run: `24618795887`
- job: `contracts`
- failing test: `src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py::test_ci_contracts_job_includes_all_contract_tests`

Observed assertion:

- missing entry in `.github/workflows/ci.yml` contracts step:
  - `src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py`

### Local verification after remediation

Executed:

```bash
PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_p2_observation_discoverability.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Result:

- `6 passed`

Executed broader PR `#250` focused suite:

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

Result:

- `20 passed`

## Outcome

PR `#250` no longer depends on an incomplete local-only verification path.

After this remediation, the same P2 observation discoverability guard is enforced in both places:

- local focused verification
- GitHub `contracts` CI job

No runtime, API, approval-chain, dashboard, export, or audit behavior changed in this slice.
