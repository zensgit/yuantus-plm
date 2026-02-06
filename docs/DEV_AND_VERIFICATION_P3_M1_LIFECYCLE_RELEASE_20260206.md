# Development & Verification: Phase 3 M1 Lifecycle Closure (2026-02-06)

## 1. Scope

This delivery closes P3 M1 lifecycle requirements with strict quality gates:

- operation lifecycle (list/update/delete/resequence),
- routing release/reopen flow,
- MBOM release/reopen flow,
- manufacturing write-permission consolidation,
- routing-workcenter scope consistency checks.

## 2. Implementation

### 2.1 Routing service lifecycle

Updated: `src/yuantus/meta_engine/manufacturing/routing_service.py`

- Added workcenter scope validation:
  - plant consistency (`routing.plant_code` vs `workcenter.plant_code`)
  - line consistency (`routing.line_code` vs `workcenter.department_code`)
- Added operation lifecycle methods:
  - `list_operations(...)`
  - `update_operation(...)`
  - `delete_operation(...)`
  - `resequence_operations(...)`
- Added routing lifecycle methods:
  - `release_routing(...)`
  - `reopen_routing(...)`
- Added line code support for routing creation.

### 2.2 MBOM lifecycle

Updated: `src/yuantus/meta_engine/manufacturing/mbom_service.py`

- Added:
  - `release_mbom(...)`
  - `reopen_mbom(...)`
- Release checks:
  - non-empty MBOM structure
  - at least one released routing linked to the MBOM

### 2.3 Manufacturing API expansion

Updated: `src/yuantus/meta_engine/web/manufacturing_router.py`

- Added operation APIs:
  - `GET /api/v1/routings/{routing_id}/operations`
  - `PATCH /api/v1/routings/{routing_id}/operations/{operation_id}`
  - `DELETE /api/v1/routings/{routing_id}/operations/{operation_id}`
  - `POST /api/v1/routings/{routing_id}/operations/resequence`
- Added routing lifecycle APIs:
  - `PUT /api/v1/routings/{routing_id}/release`
  - `PUT /api/v1/routings/{routing_id}/reopen`
- Added MBOM lifecycle APIs:
  - `PUT /api/v1/mboms/{mbom_id}/release`
  - `PUT /api/v1/mboms/{mbom_id}/reopen`
- Admin guard consolidation:
  - all manufacturing write endpoints require admin/superuser.
- Unified write error semantics:
  - `404`: resource not found
  - `400`: business rule invalid
  - `403`: permission denied

## 3. Tests

### 3.1 New tests

- `src/yuantus/meta_engine/tests/test_manufacturing_routing_lifecycle.py`
  - operation update/delete/resequence and routing release/reopen
- `src/yuantus/meta_engine/tests/test_manufacturing_mbom_release.py`
  - MBOM release/reopen checks
- `src/yuantus/meta_engine/tests/test_manufacturing_mbom_router.py`
  - MBOM lifecycle API permission and not-found mapping

### 3.2 Updated tests

- `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
  - operation lifecycle endpoints
  - routing release/reopen endpoints
  - write-permission boundary
- `src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py`
  - plant/line mismatch guardrails
- `playwright/tests/manufacturing_workcenter.spec.js`
  - operation lifecycle + routing release/reopen E2E scenario

## 4. Verification Runs

### Run P3M1-PYTEST-TARGETED-20260206-2144

- Time: `2026-02-06 21:44:01 +0800`
- Command:
  - `.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_manufacturing_routing_lifecycle.py src/yuantus/meta_engine/tests/test_manufacturing_mbom_release.py src/yuantus/meta_engine/tests/test_manufacturing_mbom_router.py src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py src/yuantus/meta_engine/tests/test_manufacturing_routing_primary.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_router.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_service.py src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py`
- Result: `PASS` (53 passed)

### Run P3M1-PYTEST-NONDB-20260206-2144

- Time: `2026-02-06 21:44:01 +0800`
- Command:
  - `.venv/bin/pytest -q`
- Result: `PASS` (16 passed)

### Run P3M1-PYTEST-DB-20260206-2144

- Time: `2026-02-06 21:44:01 +0800`
- Command:
  - `YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- Result: `PASS` (163 passed, 110 warnings)

### Run P3M1-PLAYWRIGHT-API-20260206-2144

- Time: `2026-02-06 21:44:01 +0800`
- Command:
  - `npx playwright test playwright/tests/manufacturing_workcenter.spec.js playwright/tests/config_variants_compare.spec.js`
- Result: `PASS` (5 passed)
