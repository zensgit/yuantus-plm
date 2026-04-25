# Report Router Decomposition

Date: 2026-04-24

## 1. Goal

Start a new bounded router decomposition cycle for `src/yuantus/meta_engine/web/report_router.py`.

This increment executes R1 directly instead of stopping at a docs-only gate.

## 2. R1 Boundary

R1 is locked to the saved-search surface only:

- `POST /api/v1/reports/saved-searches`
- `GET /api/v1/reports/saved-searches`
- `GET /api/v1/reports/saved-searches/{saved_search_id}`
- `PATCH /api/v1/reports/saved-searches/{saved_search_id}`
- `DELETE /api/v1/reports/saved-searches/{saved_search_id}`
- `POST /api/v1/reports/saved-searches/{saved_search_id}/run`

Target router file:

- `src/yuantus/meta_engine/web/report_saved_search_router.py`

Legacy router after R1:

- `src/yuantus/meta_engine/web/report_router.py`

The legacy router remains active and keeps all non-saved-search endpoints.

## 3. Why This Slice

This slice has the cleanest route boundary in `report_router.py`:

- exclusive `/saved-searches*` prefix;
- dedicated request/response DTOs;
- one service dependency: `SavedSearchService`;
- no overlap with dashboards, report definitions, executions, or summary/search.

## 4. Required Runtime Changes

1. Move the saved-search DTOs and six handlers into `report_saved_search_router.py`.
2. Remove those DTOs and handlers from `report_router.py`.
3. Register `report_saved_search_router` in `src/yuantus/api/app.py` before `report_router`.
4. Preserve:
   - route methods and paths,
   - `Reports` tag,
   - auth dependencies,
   - permission behavior,
   - response schema.

## 5. Required Tests

Add:

- `src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_report_saved_search_router.py`

Contract assertions must include:

1. the six moved routes are owned by `report_saved_search_router`;
2. `report_router.py` no longer declares any `/saved-searches*` decorators;
3. `app.py` registers `report_saved_search_router` before `report_router`;
4. each moved `(method, path)` is registered exactly once;
5. tags remain `Reports`.

Behavior tests must pin:

- create/list/get/update/delete/run happy paths as needed;
- `404` for missing saved search;
- `403` for private non-owner access;
- `403` for non-owner mutation;
- `page_size=0` forwarding to `None` for run behavior.

## 6. Verification

Required commands:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/report_saved_search_router.py \
  src/yuantus/meta_engine/web/report_router.py \
  src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_saved_search_router.py
```

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

```bash
git diff --check
```

## 7. Non-Goals

- No movement of `/summary` or `/search`.
- No movement of `/definitions*` or `/executions*`.
- No movement of `/dashboards*`.
- No service extraction from the `reports/` service layer.
- No public API change.
- No UI work.
- No shared-dev `142` activity.

## 8. Follow-Up Candidates

After R1 lands cleanly, the next cohesive slices are:

1. `definitions + executions`
2. `dashboards`
3. `summary + search`
