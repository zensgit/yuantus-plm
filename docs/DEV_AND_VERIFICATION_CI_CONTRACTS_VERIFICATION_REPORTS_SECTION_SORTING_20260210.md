# CI Contracts: Verification Reports Section Sorting (2026-02-10)

## Goal

Keep `docs/DELIVERY_DOC_INDEX.md` maintainable by enforcing deterministic ordering for
`## Verification Reports (Latest)`.

## Changes

- Added contract test:
  - `src/yuantus/meta_engine/tests/test_delivery_doc_index_verification_reports_sorting_contracts.py`
  - Validates:
    - non-empty primary path entries (first backticked path per bullet)
    - unique primary paths
    - lexicographically sorted primary paths
- Updated CI contracts wiring:
  - `.github/workflows/ci.yml` now runs this new test.
- Reordered section in:
  - `docs/DELIVERY_DOC_INDEX.md`
  - Section updated: `## Verification Reports (Latest)`

## Verification

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_verification_reports_sorting_contracts.py

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_core_ops_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_verification_reports_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py
```

Result: PASS

