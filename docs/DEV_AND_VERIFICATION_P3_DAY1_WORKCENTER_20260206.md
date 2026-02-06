# Development & Verification: Phase 3 Day 1 WorkCenter API Skeleton (2026-02-06)

## 1. Scope

Phase 3 MBOM/Routing capability already exists in repository.  
Day 1 focus is to close the foundational gap for manufacturing resource master data:

- Add WorkCenter service layer
- Add WorkCenter API skeleton (list/get/create/update)
- Add automated verification (pytest + Playwright)

## 2. Implementation

### 2.1 Service

- New file: `src/yuantus/meta_engine/manufacturing/workcenter_service.py`
- Added `WorkCenterService` methods:
  - `list_workcenters(...)`
  - `get_workcenter(...)`
  - `get_workcenter_by_code(...)`
  - `create_workcenter(...)`
  - `update_workcenter(...)`

### 2.2 API

- Updated file: `src/yuantus/meta_engine/web/manufacturing_router.py`
- Added router:
  - `workcenter_router = APIRouter(prefix="/workcenters", tags=["WorkCenter"])`
- Added endpoints:
  - `POST /api/v1/workcenters`
  - `GET /api/v1/workcenters`
  - `GET /api/v1/workcenters/{workcenter_id}`
  - `PATCH /api/v1/workcenters/{workcenter_id}`

### 2.3 App registration

- Updated file: `src/yuantus/api/app.py`
- Included `workcenter_router` under `/api/v1`.

## 3. Tests

### 3.1 Unit tests

- New file: `src/yuantus/meta_engine/tests/test_manufacturing_workcenter_service.py`
- Coverage:
  - required field validation
  - duplicate code rejection
  - default value behavior
  - update conflict validation
  - update field application

### 3.2 Playwright API test

- New file: `playwright/tests/manufacturing_workcenter.spec.js`
- Coverage:
  - login
  - create workcenter
  - get by id
  - update (deactivate)
  - list active-only vs include-inactive

## 4. Verification Runs

### Run P3D1-PYTEST-TARGETED-20260206-2005

- Time: `2026-02-06 20:05:13 +0800`
- Command:
  - `.venv/bin/pytest -q src/yuantus/meta_engine/tests/test_manufacturing_workcenter_service.py src/yuantus/meta_engine/tests/test_manufacturing_mbom_routing.py`
- Result: `PASS` (7 passed)

### Run P3D1-PYTEST-NONDB-20260206-2005

- Time: `2026-02-06 20:05:13 +0800`
- Command:
  - `.venv/bin/pytest -q`
- Result: `PASS` (16 passed)

### Run P3D1-PYTEST-DB-20260206-2005

- Time: `2026-02-06 20:05:13 +0800`
- Command:
  - `YUANTUS_PYTEST_DB=1 .venv/bin/pytest -q`
- Result: `PASS` (117 passed, 26 warnings)

### Run P3D1-PLAYWRIGHT-API-20260206-2005

- Time: `2026-02-06 20:05:13 +0800`
- Command:
  - `npx playwright test playwright/tests/manufacturing_workcenter.spec.js playwright/tests/config_variants_compare.spec.js`
- Result: `PASS` (2 passed)
