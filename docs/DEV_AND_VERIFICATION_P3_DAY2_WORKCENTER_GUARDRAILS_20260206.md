# Development & Verification: Phase 3 Day 2 WorkCenter Guardrails (2026-02-06)

## 1. Scope

Day 2 extends Phase 3 manufacturing foundation with two guardrails:

- Operation ↔ WorkCenter association validation
- WorkCenter write API permission control (admin-only)

## 2. Implementation

### 2.1 Routing/Operation validation

- Updated: `src/yuantus/meta_engine/manufacturing/routing_service.py`
- Added `_validate_workcenter_code(...)`
  - validates referenced WorkCenter exists
  - validates WorkCenter is active
  - normalizes trimmed code
- `add_operation(...)` now calls validation before creating operation.

### 2.2 WorkCenter API permissions

- Updated: `src/yuantus/meta_engine/web/manufacturing_router.py`
- Added `_ensure_admin(...)`
  - allows `is_superuser`
  - allows role `admin` or `superuser`
- Applied admin-only check to write endpoints:
  - `POST /api/v1/workcenters`
  - `PATCH /api/v1/workcenters/{workcenter_id}`

## 3. Tests

### 3.1 Unit tests

- New: `src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py`
  - rejects unknown workcenter code
  - rejects inactive workcenter code
  - accepts active workcenter code
- New: `src/yuantus/meta_engine/tests/test_manufacturing_workcenter_router.py`
  - create/update denied for non-admin
  - create allowed for admin

### 3.2 Playwright API regression

- Re-run:
  - `playwright/tests/manufacturing_workcenter.spec.js`
  - `playwright/tests/config_variants_compare.spec.js`

## 4. Verification Runs

### Run P3D2-PYTEST-TARGETED-20260206-2026

- Time: `2026-02-06 20:26:40 +0800`
- Command:
  - `.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_manufacturing_routing_workcenter_validation.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_router.py src/yuantus/meta_engine/tests/test_manufacturing_workcenter_service.py`
- Result: `PASS` (11 passed)

### Run P3D2-PYTEST-NONDB-20260206-2026

- Time: `2026-02-06 20:26:40 +0800`
- Command:
  - `.venv/bin/pytest -q`
- Result: `PASS` (16 passed)

### Run P3D2-PYTEST-DB-20260206-2026

- Time: `2026-02-06 20:26:40 +0800`
- Command:
  - `YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- Result: `PASS` (123 passed, 38 warnings)

### Run P3D2-PLAYWRIGHT-API-20260206-2026

- Time: `2026-02-06 20:26:40 +0800`
- Command:
  - `npx playwright test playwright/tests/manufacturing_workcenter.spec.js playwright/tests/config_variants_compare.spec.js`
- Result: `PASS` (2 passed)
