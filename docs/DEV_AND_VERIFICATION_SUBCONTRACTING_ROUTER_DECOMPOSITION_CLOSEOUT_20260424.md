# Subcontracting Router Decomposition Closeout - 2026-04-24

## 1. Scope

This increment decomposes the legacy `subcontracting_router.py` runtime routes into focused router modules while preserving the public `/api/v1/subcontracting/*` surface.

The legacy router remains registered as an empty compatibility shell.

## 2. Runtime Modules

- `src/yuantus/meta_engine/web/subcontracting_orders_router.py`
- `src/yuantus/meta_engine/web/subcontracting_analytics_router.py`
- `src/yuantus/meta_engine/web/subcontracting_approval_mapping_router.py`
- `src/yuantus/meta_engine/web/subcontracting_router.py`

## 3. Route Ownership

- `subcontracting_orders_router`: 7 routes
- `subcontracting_analytics_router`: 6 routes
- `subcontracting_approval_mapping_router`: 3 routes
- `subcontracting_router`: 0 runtime routes

## 4. App Registration

`src/yuantus/api/app.py` now registers the subcontracting routers in this order:

1. `subcontracting_orders_router`
2. `subcontracting_analytics_router`
3. `subcontracting_approval_mapping_router`
4. `subcontracting_router`

This preserves the legacy shell registration while ensuring all runtime routes are owned by focused modules.

## 5. Tests Added

- `src/yuantus/meta_engine/tests/test_subcontracting_orders_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_analytics_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_approval_mapping_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_subcontracting_router_decomposition_closeout_contracts.py`

Existing behavior tests in `test_subcontracting_router.py` were retargeted to the new owner modules.

## 6. CI Wiring

The new subcontracting contract tests are included in `.github/workflows/ci.yml`.

`test_router_decomposition_portfolio_contracts.py` now covers `subcontracting_router.py` as a registered empty shell.

## 7. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/subcontracting_orders_router.py \
  src/yuantus/meta_engine/web/subcontracting_analytics_router.py \
  src/yuantus/meta_engine/web/subcontracting_approval_mapping_router.py \
  src/yuantus/meta_engine/web/subcontracting_router.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_subcontracting_orders_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_approval_mapping_router_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_subcontracting_router.py \
  src/yuantus/meta_engine/tests/test_subcontracting_service.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
```

```bash
git diff --check
```

Observed results:

- `py_compile`: passed
- Subcontracting focused regression: `50 passed in 6.29s`
- Full router contract sweep: `267 passed in 37.30s`
- `git diff --check`: passed

## 8. Non-Goals

- No public route path changes.
- No response schema changes.
- No service-layer changes.
- No database or migration changes.
- No scheduler, CAD, ECO, BOM, report, or approval behavior changes.

## 9. Result

Subcontracting router decomposition is complete at the router ownership level. The legacy shell is still present and registered, but no runtime route is owned by it.
