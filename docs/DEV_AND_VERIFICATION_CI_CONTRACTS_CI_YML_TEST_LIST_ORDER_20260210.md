# CI Contracts: CI YAML Contracts Test List Ordering (2026-02-10)

## Goal

Keep `.github/workflows/ci.yml` contracts test wiring deterministic by enforcing:

- Unique test entries (no duplicates)
- Path-sorted test list in the `Contract checks (perf workflows + delivery doc index)` step

This reduces merge conflicts and prevents accidental drift while preserving the same executed test set.

## Changes

- Added contract test:
  - `src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py`
- Updated contracts step in:
  - `.github/workflows/ci.yml`
  - Reordered test paths to lexicographic order
  - Added the new ordering contract test to the list

## Verification

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: PASS

