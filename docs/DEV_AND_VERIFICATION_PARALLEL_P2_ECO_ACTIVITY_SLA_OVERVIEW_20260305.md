# DEV_AND_VERIFICATION_PARALLEL_P2_ECO_ACTIVITY_SLA_OVERVIEW_20260305

- Date: 2026-03-05
- Repo: `/Users/huazhou/Downloads/Github/Yuantus`
- Scope: ECO activity SLA overview API + service classification + e2e coverage.

## 1. Development Summary

Implemented SLA aggregation for ECO activities and exposed a new endpoint.

Changed files:

1. `src/yuantus/meta_engine/services/parallel_tasks_service.py`
2. `src/yuantus/meta_engine/web/parallel_tasks_router.py`
3. `src/yuantus/meta_engine/tests/test_parallel_tasks_services.py`
4. `src/yuantus/meta_engine/tests/test_parallel_tasks_router.py`
5. `src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py`

## 2. Verification Commands

1. Focused new/changed test nodes

```bash
pytest -q \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py::test_eco_activity_validation_enforces_dependency_gate \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py::test_eco_activity_sla_classification_and_filters \
  src/yuantus/meta_engine/tests/test_parallel_tasks_services.py::test_eco_activity_sla_validates_window_and_limit \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py::test_eco_activity_create_invalid_maps_contract_error \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py::test_eco_activity_transition_blocked_maps_contract_error \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py::test_eco_activity_sla_returns_overview_with_operator_id \
  src/yuantus/meta_engine/tests/test_parallel_tasks_router.py::test_eco_activity_sla_invalid_maps_contract_error \
  src/yuantus/meta_engine/tests/test_parallel_ops_router_e2e.py::test_eco_activity_sla_endpoint_e2e
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

1. Focused nodes:
- Result: `8 passed in 1.48s`

2. Affected suite bundle:
- Result: `100 passed, 337 warnings in 9.91s`

3. Contracts suite:
- Result: `142 passed in 7.60s`

4. Full meta_engine:
- Result: `162 passed, 532 warnings in 15.51s`

## 4. Contract and Behavior Checks

1. SLA classification correctness:
- Overdue / due-soon / on-track / no-due-date / closed behavior verified.

2. Filtering behavior:
- `assignee_id` filter and `include_closed` flag verified.

3. Bounds and validation:
- `due_soon_hours` and `limit` range validation verified.
- Router maps service validation failures to `eco_activity_sla_invalid`.

4. End-to-end behavior:
- API create -> transition -> SLA read path verified against real DB setup.

## 5. Failure Samples and Handling

1. Invalid SLA window/limit:
- Service raises `ValueError` with deterministic message.
- Router returns `400` + `eco_activity_sla_invalid` + request context.

2. Invalid evaluated datetime:
- Router reuses `invalid_datetime` contract with field-level context.
