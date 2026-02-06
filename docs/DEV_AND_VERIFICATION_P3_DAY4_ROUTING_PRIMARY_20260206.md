# Development & Verification: Phase 3 Day 4 Routing Primary Control (2026-02-06)

## 1. Scope

Phase 3 Day 4 focuses on routing lifecycle consistency:

- enforce single primary routing per scope (`item_id` or `mbom_id`),
- provide explicit API to switch primary routing,
- provide routing list API for scoped query.

## 2. Implementation

### 2.1 Routing service

Updated: `src/yuantus/meta_engine/manufacturing/routing_service.py`

- Added routing scope helpers:
  - `_scope_filters(...)`
  - `_clear_primary_in_scope(...)`
- Enhanced `create_routing(...)`:
  - if `is_primary=true`, automatically clears primary flag on sibling routings
    in the same scope.
- Added `list_routings(...)` with optional filters:
  - `mbom_id`
  - `item_id`
- Added `set_primary_routing(...)`:
  - validates routing exists,
  - validates routing has a valid scope,
  - clears sibling primary flags and sets target routing as primary.

### 2.2 Manufacturing router API

Updated: `src/yuantus/meta_engine/web/manufacturing_router.py`

- Added endpoint:
  - `GET /api/v1/routings` (optional `mbom_id` / `item_id` query filters)
- Added endpoint:
  - `PUT /api/v1/routings/{routing_id}/primary`
  - admin-only (`_ensure_admin`)
  - maps not-found to `404`.

## 3. Tests

### 3.1 Unit/API tests

- New: `src/yuantus/meta_engine/tests/test_manufacturing_routing_primary.py`
  - create primary routing clears existing primary in same scope
  - set primary switches correctly
  - missing scope rejected
  - not found rejected
- Updated: `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
  - list routings API response contract
  - set primary permission guard
  - set primary success path
  - set primary not-found mapping (404)

### 3.2 Playwright API test

Updated: `playwright/tests/manufacturing_workcenter.spec.js`

- Added scenario:
  - create routing A/B in same item scope,
  - switch primary to B,
  - verify A is no longer primary and list endpoint returns a single primary.

## 4. Verification Runs

### Run P3D4-PYTEST-TARGETED-20260206-2116

- Time: `2026-02-06 21:16:15 +0800`
- Command:
  - `.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_manufacturing_routing_primary.py src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_router.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_service.py`
- Result: `PASS` (26 passed)

### Run P3D4-PYTEST-NONDB-20260206-2116

- Time: `2026-02-06 21:16:15 +0800`
- Command:
  - `.venv/bin/pytest -q`
- Result: `PASS` (16 passed)

### Run P3D4-PYTEST-DB-20260206-2116

- Time: `2026-02-06 21:16:15 +0800`
- Command:
  - `YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- Result: `PASS` (138 passed, 62 warnings)

### Run P3D4-PLAYWRIGHT-API-20260206-2116

- Time: `2026-02-06 21:16:15 +0800`
- Command:
  - `npx playwright test playwright/tests/manufacturing_workcenter.spec.js playwright/tests/config_variants_compare.spec.js`
- Result: `PASS` (4 passed)
