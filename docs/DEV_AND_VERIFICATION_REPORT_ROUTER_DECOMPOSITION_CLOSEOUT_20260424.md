# DEV_AND_VERIFICATION_REPORT_ROUTER_DECOMPOSITION_CLOSEOUT_20260424

## Scope

This closeout seals the report router decomposition after R1 saved-search extraction.
It completes the remaining runtime split for:

- `/api/v1/reports/summary`
- `/api/v1/reports/search`
- `/api/v1/reports/definitions*`
- `/api/v1/reports/executions*`
- `/api/v1/reports/dashboards*`

Legacy `report_router.py` remains registered as an empty compatibility shell.

## Runtime Changes

- `src/yuantus/meta_engine/web/report_summary_search_router.py`
  - Owns `/summary` and `/search`
- `src/yuantus/meta_engine/web/report_definition_router.py`
  - Owns `/definitions*` and `/executions*`
- `src/yuantus/meta_engine/web/report_dashboard_router.py`
  - Owns `/dashboards*`
- `src/yuantus/meta_engine/web/report_router.py`
  - Reduced to an empty `APIRouter` shell
- `src/yuantus/api/app.py`
  - Registers routers in decomposition order:
    `report_saved_search_router -> report_summary_search_router -> report_definition_router -> report_dashboard_router -> report_router`

## Test Additions

- `src/yuantus/meta_engine/tests/test_report_definition_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_report_dashboard_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_report_summary_search_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_report_router_decomposition_closeout_contracts.py`
- `src/yuantus/meta_engine/tests/test_report_definition_router.py`
- `src/yuantus/meta_engine/tests/test_report_dashboard_router.py`
- `src/yuantus/meta_engine/tests/test_report_summary_search_router.py`

## Test Updates

- `src/yuantus/meta_engine/tests/test_report_router_permissions.py`
  - Patch targets moved from `report_router` to `report_definition_router` and `report_summary_search_router`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
  - Added `report_router.py` to legacy shell inventory
  - Added report decomposition contract files to portfolio CI surface
- `.github/workflows/ci.yml`
  - Added report router decomposition contracts to the contracts job

## Verification

Executed after the closeout landed in the working tree:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/report_saved_search_router.py \
  src/yuantus/meta_engine/web/report_summary_search_router.py \
  src/yuantus/meta_engine/web/report_definition_router.py \
  src/yuantus/meta_engine/web/report_dashboard_router.py \
  src/yuantus/meta_engine/web/report_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_report_saved_search_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_summary_search_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_definition_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_dashboard_router_contracts.py \
  src/yuantus/meta_engine/tests/test_report_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_report_saved_search_router.py \
  src/yuantus/meta_engine/tests/test_report_summary_search_router.py \
  src/yuantus/meta_engine/tests/test_report_definition_router.py \
  src/yuantus/meta_engine/tests/test_report_dashboard_router.py \
  src/yuantus/meta_engine/tests/test_report_router_permissions.py \
  src/yuantus/meta_engine/tests/test_reports_advanced_search.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## Results

- `py_compile` passed for all 5 report router modules
- Report-focused regression:
  - `67 passed in 14.00s`
- Broad router-contract sweep:
  - `221 passed in 30.19s`
- `git diff --check` passed

## Final State

- `/api/v1/reports/*` now resolves through 4 specialized routers plus 1 registered empty shell
- Specialized ownership split:
  - `report_saved_search_router`: 6 routes
  - `report_summary_search_router`: 2 routes
  - `report_definition_router`: 9 routes
  - `report_dashboard_router`: 5 routes
  - `report_router`: 0 runtime routes

## Expected Outcome

- All `/api/v1/reports/*` runtime routes are owned by specialized routers, never by `report_router`
- `report_router.py` stays imported and registered intentionally as a zero-handler shell
- Public API paths, methods, tags, and handler behavior stay stable
- CI contracts explicitly cover the report family and the portfolio inventory

## Non-Goals

- No report service refactor
- No schema change
- No auth middleware policy change
- No UI/report payload redesign
- No shared-dev deployment action
