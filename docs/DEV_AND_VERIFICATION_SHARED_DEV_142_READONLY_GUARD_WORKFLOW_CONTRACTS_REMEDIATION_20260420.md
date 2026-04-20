# DEV AND VERIFICATION - SHARED DEV 142 READONLY GUARD WORKFLOW CONTRACTS REMEDIATION - 2026-04-20

## Background

- `#289` merged the new `.github/workflows/shared-dev-142-readonly-guard.yml` workflow into `main`.
- The post-merge docs follow-up `#290` then failed repo-wide workflow contracts.
- The failing checks showed three concrete violations:
  - concurrency group did not include `github.workflow`
  - concurrency group did not match the repo template `${{ github.workflow }}-${{ github.ref }}`
  - `actions: write` was required by the workflow logic but missing from the least-privilege allowlist

## Changes

- Updated `.github/workflows/shared-dev-142-readonly-guard.yml`
  - `concurrency.group` now uses `${{ github.workflow }}-${{ github.ref }}`
- Updated `src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py`
  - added `shared-dev-142-readonly-guard.yml` to the `actions: write` allowlist
- Updated `src/yuantus/meta_engine/tests/test_shared_dev_142_readonly_guard_workflow_contracts.py`
  - aligned the workflow-specific contract test to the repo-standard concurrency template

## Verification

Executed from an isolated worktree rooted at the merged `#289` baseline plus this remediation:

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_all_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_group_template_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_permissions_least_privilege_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_permissions_contracts.py \
  src/yuantus/meta_engine/tests/test_shared_dev_142_readonly_guard_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

Observed result:

- `8 passed in 0.31s`
- workflow concurrency contracts passed
- workflow permissions contracts passed
- workflow-specific shared-dev 142 guard contracts passed
- delivery/dev-verification doc index contracts passed

## Outcome

- This is a narrow contracts remediation.
- No business logic, shared-dev baseline content, or readonly evaluation logic changed.
- The only behavioral change is that the guard workflow now conforms to the repo-wide workflow governance tests.
