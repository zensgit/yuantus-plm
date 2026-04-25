# DEV_AND_VERIFICATION_APPROVALS_ROUTER_DECOMPOSITION_CLOSEOUT_20260424

## Scope

This closeout decomposes the generic approvals HTTP surface into 3 specialized routers:

- categories
- requests
- ops / reporting / queue-health

Legacy `approvals_router.py` remains imported and registered as an empty compatibility shell.

## Runtime Changes

- `src/yuantus/meta_engine/web/approval_category_router.py`
  - Owns `POST/GET /api/v1/approvals/categories`
- `src/yuantus/meta_engine/web/approval_request_router.py`
  - Owns all `/api/v1/approvals/requests*` routes
- `src/yuantus/meta_engine/web/approval_ops_router.py`
  - Owns `/summary*`, `/ops-report*`, `/queue-health*`
- `src/yuantus/meta_engine/web/approvals_router.py`
  - Reduced to an empty `APIRouter` shell
- `src/yuantus/api/app.py`
  - Registers routers in decomposition order:
    `approval_category_router -> approval_request_router -> approval_ops_router -> approvals_router`

## Test Changes

- Added route ownership contracts:
  - `src/yuantus/meta_engine/tests/test_approval_category_router_contracts.py`
  - `src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py`
  - `src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py`
  - `src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py`
- Updated `src/yuantus/meta_engine/tests/test_approvals_router.py`
  - behavior coverage kept in one file
  - patch targets moved from `approvals_router` to specialized routers
  - helper app now includes specialized routers plus the legacy shell
- Updated `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
  - adds `approvals_router.py` to the registered-shell inventory
  - adds approvals decomposition contracts to portfolio CI surface
- Updated `.github/workflows/ci.yml`
  - approvals contract tests are part of the contracts job

## Verification

Executed after the decomposition landed in the working tree:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/approval_category_router.py \
  src/yuantus/meta_engine/web/approval_request_router.py \
  src/yuantus/meta_engine/web/approval_ops_router.py \
  src/yuantus/meta_engine/web/approvals_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_approval_category_router_contracts.py \
  src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py \
  src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_approvals_service.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

## Results

- `py_compile` passed for all 4 approvals router modules
- Approvals-focused regression:
  - `75 passed in 6.23s`
- Combined report + approvals regression on the current working tree:
  - `132 passed in 18.40s`
- Broad router-contract sweep:
  - `244 passed in 34.49s`
- `git diff --check` passed

## Final State

- `/api/v1/approvals/*` now resolves through 3 specialized routers plus 1 registered empty shell
- Specialized ownership split:
  - `approval_category_router`: 2 routes
  - `approval_request_router`: 9 routes
  - `approval_ops_router`: 6 routes
  - `approvals_router`: 0 runtime routes

## Expected Outcome

- All `/api/v1/approvals/*` runtime routes are owned by specialized routers
- `approvals_router.py` stays registered intentionally as a zero-handler shell
- No public API path or method changes
- CI and portfolio contracts explicitly pin the new ownership map

## Non-Goals

- No approval service refactor
- No auth model change
- No scheduler change
- No ECO approval workflow change
- No shared-dev deployment activity
