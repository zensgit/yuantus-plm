# Dev Log (2026-02-15): verify_all `is_truthy` Definition Order

## Context

`scripts/verify_all.sh` called `is_truthy` before the function was defined.
In shell runtime this may print `command not found` and make branch decisions depend on fallback expression behavior.

## Changes

1. Fixed helper definition order in `scripts/verify_all.sh`.

- Moved `is_truthy()` above the first invocation site.
- Removed duplicated later definition.

2. Added CI contract coverage.

- New test: `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_is_truthy_order.py`
- Asserts `is_truthy()` is defined before first non-comment invocation in `scripts/verify_all.sh`.

3. Wired into CI contracts job.

- Updated `.github/workflows/ci.yml` test list to include:
  - `src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_is_truthy_order.py`

## Verification

Executed:

```bash
./.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_is_truthy_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_env_allowlist.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py
```

Result:

- `6 passed in 0.44s`

Executed:

```bash
./.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_change_scope_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_import_dedup_index.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_compose_worker_dedup_vision_url.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_auto_trigger_workflow.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_batch_run_index.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_job_promotion.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_report_endpoints.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_similarity_pair_key.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_vision_host_fallback.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_vision_v2_fallback.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_vision_verify_script_docker_worker.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_dedup_vision_verify_scripts_port_override.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_env_allowlist.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_verify_all_is_truthy_order.py \
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
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py
```

Result:

- `48 passed in 3.30s`

Runtime smoke:

```bash
RUN_DEDUP=1 bash scripts/verify_all.sh http://127.0.0.1:9
```

Observed:

- No `is_truthy: command not found` in output.
- Script fails correctly at API preflight (`HTTP 000000`) due intentionally unreachable endpoint.
