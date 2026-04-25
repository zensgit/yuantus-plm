# Cutted Parts Router Decomposition Closeout

Date: 2026-04-24

## Scope

This closeout completes the `/api/v1/cutted-parts` router decomposition.
The legacy `cutted_parts_router.py` is now an empty compatibility shell and
all 44 public cutted-parts routes are owned by focused split routers.

## Router Map

- `cutted_parts_core_router.py`: 6 core plan/material endpoints.
- `cutted_parts_analytics_router.py`: 5 overview, material analytics, and waste export endpoints.
- `cutted_parts_utilization_router.py`: 5 cost and utilization endpoints.
- `cutted_parts_scenarios_router.py`: 4 template and scenario endpoints.
- `cutted_parts_benchmark_router.py`: 4 benchmark and quote endpoints.
- `cutted_parts_variance_router.py`: 4 variance and recommendation endpoints.
- `cutted_parts_thresholds_router.py`: 4 threshold and envelope endpoints.
- `cutted_parts_alerts_router.py`: 4 alert and outlier endpoints.
- `cutted_parts_throughput_router.py`: 4 throughput and cadence endpoints.
- `cutted_parts_bottlenecks_router.py`: 4 saturation and bottleneck endpoints.

## Design

The change is a mechanical route relocation:

- Request and response behavior is preserved.
- Existing service calls are unchanged.
- Existing `ValueError -> 404` and plan creation `ValueError -> 400` mappings are preserved.
- The legacy router remains registered as an empty shell to avoid import and registration churn.

`create_app()` registers all split routers before the legacy shell. This gives
deterministic ownership and prevents accidental reintroduction of runtime route
handlers into `cutted_parts_router.py`.

## Contracts

`test_cutted_parts_router_decomposition_closeout_contracts.py` pins:

- `cutted_parts_router.py` declares no runtime route decorators.
- All 44 cutted-parts route `(method, path)` pairs resolve to expected split modules.
- Every cutted-parts route is registered exactly once.
- All split routers are registered before the legacy shell.
- All routes preserve the public `Cutted Parts` tag.

`test_router_decomposition_portfolio_contracts.py` now includes
`cutted_parts_router.py` in the empty legacy-shell portfolio.

## Files

- `src/yuantus/meta_engine/web/cutted_parts_core_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_analytics_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_utilization_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_scenarios_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_benchmark_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_variance_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_thresholds_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_alerts_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_throughput_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_bottlenecks_router.py`
- `src/yuantus/meta_engine/web/cutted_parts_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py`
- `src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_closeout_contracts.py`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## Verification

Commands executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cutted_parts_core_router.py \
  src/yuantus/meta_engine/web/cutted_parts_router.py \
  src/yuantus/meta_engine/web/cutted_parts_analytics_router.py \
  src/yuantus/meta_engine/web/cutted_parts_utilization_router.py \
  src/yuantus/meta_engine/web/cutted_parts_scenarios_router.py \
  src/yuantus/meta_engine/web/cutted_parts_benchmark_router.py \
  src/yuantus/meta_engine/web/cutted_parts_variance_router.py \
  src/yuantus/meta_engine/web/cutted_parts_thresholds_router.py \
  src/yuantus/meta_engine/web/cutted_parts_alerts_router.py \
  src/yuantus/meta_engine/web/cutted_parts_throughput_router.py \
  src/yuantus/meta_engine/web/cutted_parts_bottlenecks_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cutted_parts_router.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_r1_contracts.py \
  src/yuantus/meta_engine/tests/test_cutted_parts_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -m pytest -q $(rg --files src/yuantus/meta_engine/tests | rg 'router.*contracts\.py$|legacy_router_contracts\.py$')

bash -n scripts/verify_odoo18_plm_stack.sh

git diff --check
```

Result:

- `py_compile` passed.
- Focused cutted-parts closeout regression: `73 passed in 4.71s`.
- Doc index and CI list contracts: `4 passed in 0.03s`.
- Router contract sweep: `343 passed in 53.38s`.
- `bash -n scripts/verify_odoo18_plm_stack.sh` passed.
- `git diff --check` passed.

## Non-Goals

- No service-layer refactor.
- No behavior, schema, or migration change.
- No 142/shared-dev smoke; this is route ownership decomposition only.
