# Box Router Decomposition Closeout

Date: 2026-04-24

## Scope

This closeout completes the `/api/v1/box` router decomposition. The legacy
`box_router.py` is now an empty compatibility shell and all 42 public PLM Box
routes are owned by focused split routers.

## Router Map

- `box_core_router.py`: 5 core item and content endpoints.
- `box_analytics_router.py`: 5 analytics and contents export endpoints.
- `box_ops_router.py`: 4 transition and operations report endpoints.
- `box_reconciliation_router.py`: 4 reconciliation and audit endpoints.
- `box_capacity_router.py`: 4 capacity and compliance endpoints.
- `box_policy_router.py`: 4 policy and exception endpoints.
- `box_traceability_router.py`: 4 reservation and traceability endpoints.
- `box_custody_router.py`: 4 allocation and custody endpoints.
- `box_turnover_router.py`: 4 occupancy and turnover endpoints.
- `box_aging_router.py`: 4 dwell and aging endpoints.

## Design

The change is a mechanical route relocation:

- Request and response behavior is preserved.
- Existing `BoxService` calls are unchanged.
- Existing `ValueError -> 404` mappings are preserved.
- Core item creation still commits on success and rolls back on validation failure.
- The legacy router remains registered as an empty shell to keep import and registration compatibility.

`create_app()` registers all split routers before the legacy shell. This pins
deterministic route ownership and prevents route handlers from being
reintroduced into `box_router.py`.

## Contracts

`test_box_router_decomposition_closeout_contracts.py` pins:

- `box_router.py` declares no runtime route decorators.
- All 42 Box route `(method, path)` pairs resolve to expected split modules.
- Every Box route is registered exactly once.
- All split routers are registered before the legacy shell.
- All routes preserve the public `PLM Box` tag.

`test_router_decomposition_portfolio_contracts.py` now includes
`box_router.py` in the empty legacy-shell portfolio.

## Files

- `src/yuantus/meta_engine/web/box_core_router.py`
- `src/yuantus/meta_engine/web/box_analytics_router.py`
- `src/yuantus/meta_engine/web/box_ops_router.py`
- `src/yuantus/meta_engine/web/box_reconciliation_router.py`
- `src/yuantus/meta_engine/web/box_capacity_router.py`
- `src/yuantus/meta_engine/web/box_policy_router.py`
- `src/yuantus/meta_engine/web/box_traceability_router.py`
- `src/yuantus/meta_engine/web/box_custody_router.py`
- `src/yuantus/meta_engine/web/box_turnover_router.py`
- `src/yuantus/meta_engine/web/box_aging_router.py`
- `src/yuantus/meta_engine/web/box_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_box_router.py`
- `src/yuantus/meta_engine/tests/test_box_router_decomposition_closeout_contracts.py`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## Verification

Commands executed:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/box_core_router.py \
  src/yuantus/meta_engine/web/box_analytics_router.py \
  src/yuantus/meta_engine/web/box_ops_router.py \
  src/yuantus/meta_engine/web/box_reconciliation_router.py \
  src/yuantus/meta_engine/web/box_capacity_router.py \
  src/yuantus/meta_engine/web/box_policy_router.py \
  src/yuantus/meta_engine/web/box_traceability_router.py \
  src/yuantus/meta_engine/web/box_custody_router.py \
  src/yuantus/meta_engine/web/box_turnover_router.py \
  src/yuantus/meta_engine/web/box_aging_router.py \
  src/yuantus/meta_engine/web/box_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_box_router.py \
  src/yuantus/meta_engine/tests/test_box_router_decomposition_closeout_contracts.py \
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
- Focused Box closeout regression: `65 passed in 4.02s`.
- Doc index and CI list contracts: `4 passed in 0.03s`.
- Router contract sweep: `348 passed in 55.75s`.
- `bash -n scripts/verify_odoo18_plm_stack.sh` passed.
- `git diff --check` passed.

## Non-Goals

- No service-layer refactor.
- No behavior, schema, or migration change.
- No 142/shared-dev smoke; this is route ownership decomposition only.
