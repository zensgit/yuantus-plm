# Maintenance Router Decomposition Closeout - 2026-04-24

## 1. Scope

This increment decomposes the legacy `maintenance_router.py` runtime routes into focused router modules while preserving the public `/api/v1/maintenance/*` surface.

The legacy router remains registered as an empty compatibility shell.

## 2. Runtime Modules

- `src/yuantus/meta_engine/web/maintenance_category_router.py`
- `src/yuantus/meta_engine/web/maintenance_equipment_router.py`
- `src/yuantus/meta_engine/web/maintenance_request_router.py`
- `src/yuantus/meta_engine/web/maintenance_schedule_router.py`
- `src/yuantus/meta_engine/web/maintenance_router.py`

## 3. Route Ownership

- `maintenance_category_router`: 2 routes
- `maintenance_equipment_router`: 5 routes
- `maintenance_request_router`: 4 routes
- `maintenance_schedule_router`: 2 routes
- `maintenance_router`: 0 runtime routes

## 4. App Registration

`src/yuantus/api/app.py` now registers the maintenance routers in this order:

1. `maintenance_category_router`
2. `maintenance_equipment_router`
3. `maintenance_request_router`
4. `maintenance_schedule_router`
5. `maintenance_router`

This preserves the legacy shell registration while ensuring all runtime routes are owned by focused modules.

## 5. Tests Added

- `src/yuantus/meta_engine/tests/test_maintenance_category_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_maintenance_equipment_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_maintenance_request_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_maintenance_schedule_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_maintenance_router_decomposition_closeout_contracts.py`

Existing behavior tests in `test_maintenance_router.py` were retargeted to the new owner modules.

## 6. CI Wiring

The new maintenance contract tests are included in `.github/workflows/ci.yml`.

`test_router_decomposition_portfolio_contracts.py` now covers `maintenance_router.py` as a registered empty shell.

## 7. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/maintenance_category_router.py \
  src/yuantus/meta_engine/web/maintenance_equipment_router.py \
  src/yuantus/meta_engine/web/maintenance_request_router.py \
  src/yuantus/meta_engine/web/maintenance_schedule_router.py \
  src/yuantus/meta_engine/web/maintenance_router.py \
  src/yuantus/api/app.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_maintenance_category_router_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_equipment_router_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_request_router_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_schedule_router_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_maintenance_router.py \
  src/yuantus/meta_engine/tests/test_maintenance_service.py \
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
- Maintenance focused regression: `74 passed in 7.01s`
- Report + approvals + subcontracting + maintenance combined regression: `236 passed in 28.39s`
- Full router contract sweep: `296 passed in 42.62s`
- `git diff --check`: passed

## 8. Non-Goals

- No public route path changes.
- No response schema changes.
- No service-layer changes.
- No database or migration changes.
- No scheduler, CAD, ECO, BOM, report, approval, or subcontracting behavior changes.

## 9. Result

Maintenance router decomposition is complete at the router ownership level. The legacy shell is still present and registered, but no runtime route is owned by it.
