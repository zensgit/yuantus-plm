# CI Contracts: DB CLI Identity + Migration Coverage (2026-02-12)

## Goal

Lock two high-risk infra contracts so regressions fail fast in CI:

- `yuantus db` migration targeting behavior (`--identity` and `--db-url`)
- ORM table declarations remain covered by Alembic `op.create_table` history

## Changes

- Added CLI migration target contract test:
  - `src/yuantus/meta_engine/tests/test_db_cli_identity_contracts.py`
  - Enforces:
    - `--db-url` and `--identity` are mutually exclusive
    - `--identity` prefers `YUANTUS_IDENTITY_DATABASE_URL`
    - `--identity` falls back to `YUANTUS_DATABASE_URL` when identity URL is empty
    - `--db-url` forces Alembic target URL override
- Added migration coverage contract test:
  - `src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py`
  - Enforces:
    - every ORM table in `Base` + `WorkflowBase` has at least one `op.create_table(...)` migration
    - migration-only tables are explicit allowlist only (currently `audit_logs`)
- Updated CI contract wiring:
  - `.github/workflows/ci.yml` now executes both new contract tests
- Indexed this evidence doc:
  - `docs/DELIVERY_DOC_INDEX.md` under `## Development & Verification`

## Verification

```bash
python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_db_cli_identity_contracts.py \
  src/yuantus/meta_engine/tests/test_migration_table_coverage_contracts.py

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

