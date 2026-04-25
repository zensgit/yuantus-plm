# Report Router Decomposition R1 - Saved Searches

Date: 2026-04-24

## 1. Scope

Execute R1 of the report router decomposition by moving the saved-search surface out of `report_router.py` into a dedicated router.

Moved endpoints:

- `POST /api/v1/reports/saved-searches`
- `GET /api/v1/reports/saved-searches`
- `GET /api/v1/reports/saved-searches/{saved_search_id}`
- `PATCH /api/v1/reports/saved-searches/{saved_search_id}`
- `DELETE /api/v1/reports/saved-searches/{saved_search_id}`
- `POST /api/v1/reports/saved-searches/{saved_search_id}/run`

## 2. Files Changed

- `docs/DEVELOPMENT_CLAUDE_TASK_REPORT_ROUTER_DECOMPOSITION_20260424.md`
- `docs/DEV_AND_VERIFICATION_REPORT_ROUTER_DECOMPOSITION_R1_SAVED_SEARCHES_20260424.md`
- `src/yuantus/meta_engine/web/report_saved_search_router.py`
- `src/yuantus/meta_engine/web/report_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_report_saved_search_router.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Implementation Notes

- Added `report_saved_search_router.py` with the saved-search DTOs and six moved handlers.
- Kept the public `/api/v1/reports/*` paths unchanged.
- Registered `report_saved_search_router` before `report_router` in `create_app()`.
- Removed moved DTOs and handlers from `report_router.py`.
- Left summary/search, definitions/executions, and dashboards in the legacy router for later slices.

## 4. Contracts

Added `test_report_saved_search_router_contracts.py` to pin:

- route ownership,
- absence of `/saved-searches*` decorators from `report_router.py`,
- registration order,
- unique `(method, path)` registration,
- preserved `Reports` tag,
- source declaration order in the new router.

## 5. Behavior Tests

Added `test_report_saved_search_router.py` to cover:

- create happy path,
- list include_public forwarding,
- missing saved search `404`,
- private non-owner `403`,
- non-owner mutation `403`,
- owner delete happy path,
- `page_size=0` forwarded as `None` for run behavior.

## 6. Verification

Commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/report_saved_search_router.py \
  src/yuantus/meta_engine/web/report_router.py \
  src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_saved_search_router.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_saved_search_router.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py \
  src/yuantus/meta_engine/tests/test_reports_advanced_search.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `32 passed`.

```bash
git diff --check
```

Result: passed.

## 7. Non-Goals

- No movement of report definitions or executions.
- No movement of dashboards.
- No movement of summary/search.
- No service extraction from `yuantus.meta_engine.reports.*`.
- No scheduler, shared-dev, or UI changes.
