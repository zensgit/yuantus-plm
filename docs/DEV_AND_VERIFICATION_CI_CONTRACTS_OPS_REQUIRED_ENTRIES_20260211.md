# CI Contracts: Ops Required Entries (2026-02-11)

## Goal

Prevent accidental removal of critical operations anchors from
`docs/DELIVERY_DOC_INDEX.md` `## Ops & Deployment`.

## Changes

- Added contract test:
  - `src/yuantus/meta_engine/tests/test_delivery_doc_index_ops_required_entries_contracts.py`
- Required ops anchors:
  - `docs/OPS_RUNBOOK_MT.md`
  - `docs/ERROR_CODES_JOBS.md`
  - `docs/RUNBOOK_RUNTIME.md`
  - `docs/RUNBOOK_BACKUP_RESTORE.md`
  - `docs/RUNBOOK_CI_CHANGE_SCOPE.md`
  - `docs/RUNBOOK_STRICT_GATE.md`
- Updated CI contracts wiring:
  - `.github/workflows/ci.yml` now runs this new contract test
- Indexed this evidence doc:
  - `docs/DELIVERY_DOC_INDEX.md` under `## Development & Verification`

## Verification

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_ops_required_entries_contracts.py

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_all_sections_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_core_ops_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_core_required_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_external_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_ops_required_entries_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_product_optional_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_section_headings_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_verification_reports_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_strict_gate_workflow_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_concurrency_contracts.py \
  src/yuantus/meta_engine/tests/test_workflow_label_override_contracts.py
```

Result: PASS

