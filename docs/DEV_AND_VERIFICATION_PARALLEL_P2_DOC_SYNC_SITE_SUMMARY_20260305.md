# DEV_AND_VERIFICATION_PARALLEL_P2_DOC_SYNC_SITE_SUMMARY_20260305

- Date: 2026-03-05
- Repo: `/Users/huazhou/Downloads/Github/Yuantus`
- Scope: document multi-site sync summary API (`/api/v1/doc-sync/summary`).

## 1. Development Summary

Added site-level sync aggregation in service and exposed it via router contract endpoint.

Changed files:

1. `src/yuantus/meta_engine/services/parallel_tasks_service.py`
2. `src/yuantus/meta_engine/web/parallel_tasks_router.py`
3. `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
4. `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
5. `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`

## 2. Verification Commands

1. Focused tests

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py::test_document_multi_site_sync_summary_by_site_and_window \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py::test_doc_sync_summary_returns_operator_id_and_payload \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py::test_doc_sync_summary_invalid_maps_contract_error \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py::test_doc_sync_summary_endpoint_e2e
```

2. Affected suite bundle

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py
```

3. Contracts suite + full meta_engine regression

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_*contracts*.py \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_perf_gate_config_file.py \
  src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py \
  src/yuantus/meta_engine/tests/test_readme_runbook_references.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

pytest -q src/yuantus/meta_engine/tests
```

## 3. Verification Results

1. Focused tests:
- Result: `4 passed, 22 warnings in 1.57s`

2. Affected suite bundle:
- Result: `104 passed, 352 warnings in 10.59s`

3. Contracts suite:
- Result: `142 passed in 7.45s`

4. Full meta_engine:
- Result: `165 passed, 542 warnings in 15.76s`

## 4. Behavior Validation

1. Window filtering:
- Jobs older than `window_days` are excluded from totals.

2. Site grouping:
- Response includes multi-site buckets with per-site status and direction counts.

3. Dead-letter detection:
- Failed jobs with exhausted retry budget count into `dead_letter_total`.

4. API contract:
- Success path includes `operator_id`.
- Invalid `window_days` maps to `doc_sync_summary_invalid` (`400`) with context.
