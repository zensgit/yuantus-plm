# CI Contracts: Job Queue Transaction Boundary (2026-02-12)

## Goal

Prevent accidental regressions in the job queue concurrency invariants:

- PostgreSQL workers must claim jobs with `FOR UPDATE SKIP LOCKED` to avoid double-processing.
- A claim must update `status/worker_id/started_at/attempt_count` before commit.
- Queue filters/order must remain aligned with the queue index for stable performance.
- Stale requeue queries must have a supporting index.

## Changes

- Added contract test:
  - `src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py`
  - Enforces:
    - `poll_next_job()` uses `with_for_update(skip_locked=True)` under PostgreSQL
    - claim fields are updated before commit
    - pending queue filters/order remain stable
- Added migration index for stale job requeue:
  - `migrations/versions/x1b2c3d4e7a2_add_job_stale_index.py`
  - Adds `ix_meta_conversion_jobs_stale` on (`status`, `started_at`)
- Updated CI contracts wiring:
  - `.github/workflows/ci.yml` now runs this new contract test
- Updated plan status:
  - `docs/DEVELOPMENT_PLAN.md` marks the item complete
- Indexed this evidence doc:
  - `docs/DELIVERY_DOC_INDEX.md` under `## Development & Verification`

## Verification

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py

python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_db_cli_identity_contracts.py \
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
  src/yuantus/meta_engine/tests/test_job_queue_tx_boundary_contracts.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py \
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

