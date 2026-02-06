# Development & Verification: Phase 3 Day 3 WorkCenter Association (2026-02-06)

## 1. Scope

Phase 3 Day 3 focuses on strengthening operation-to-workcenter linkage:

- Support strong association via `workcenter_id`
- Keep backward compatibility with existing `workcenter_code`
- Enforce consistency when both id and code are provided

## 2. Implementation

### 2.1 Routing service association logic

- Updated file: `src/yuantus/meta_engine/manufacturing/routing_service.py`
- Added `_resolve_workcenter(...)`:
  - accepts `workcenter_id` / `workcenter_code`
  - validates existence
  - validates active status
  - validates id/code consistency when both are provided
  - returns canonical `(workcenter_id, workcenter_code)`
- `add_operation(...)` now:
  - accepts `workcenter_id`
  - persists both `workcenter_id` and normalized `workcenter_code`
- `copy_routing(...)` now preserves `workcenter_id` in copied operations.

### 2.2 Router request/response alignment

- Updated file: `src/yuantus/meta_engine/web/manufacturing_router.py`
- `OperationCreateRequest` now supports `workcenter_id`
- `OperationResponse` now includes:
  - `workcenter_id`
  - `workcenter_code`
- `POST /api/v1/routings/{routing_id}/operations` now forwards `workcenter_id` to service.

## 3. Tests

### 3.1 New/updated unit tests

- Updated: `src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py`
  - unknown/inactive code rejected
  - active code accepted and id populated
  - id-only association accepted
  - id/code mismatch rejected
  - unknown/inactive id rejected
  - copy routing preserves id+code
- New: `src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py`
  - API returns 400 when service rejects inactive workcenter
  - API response includes both `workcenter_id` and `workcenter_code`

### 3.2 Playwright API validation

- Updated: `playwright/tests/manufacturing_workcenter.spec.js`
  - added routing operation validation scenario:
    - success with active `workcenter_id`
    - 400 on id/code mismatch
    - 400 on inactive workcenter code

## 4. Verification Runs

### Run P3D3-PYTEST-TARGETED-20260206-2102

- Time: `2026-02-06 21:02:27 +0800`
- Command:
  - `.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_router.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_service.py`
- Result: `PASS` (18 passed)

### Run P3D3-PYTEST-NONDB-20260206-2102

- Time: `2026-02-06 21:02:27 +0800`
- Command:
  - `.venv/bin/pytest -q`
- Result: `PASS` (16 passed)

### Run P3D3-PYTEST-DB-20260206-2102

- Time: `2026-02-06 21:02:27 +0800`
- Command:
  - `YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- Result: `PASS` (130 passed, 46 warnings)

### Run P3D3-PLAYWRIGHT-API-20260206-2102

- Time: `2026-02-06 21:02:27 +0800`
- Command:
  - `npx playwright test playwright/tests/manufacturing_workcenter.spec.js playwright/tests/config_variants_compare.spec.js`
- Result: `PASS` (3 passed)
