# DEV_AND_VERIFICATION_APPROVALS_ROUTER_DECOMPOSITION_CLOSEOUT_UNREGISTRATION_20260425

## Scope

This is the closeout follow-up for approvals router decomposition:
- keep `approvals_router.py` as a compatibility shell, but remove it from production
  `create_app()` wiring (no import and no `include_router`).

## Changes

- `src/yuantus/api/app.py`
  - remove `approvals_router` import and `app.include_router(approvals_router, ...)`.
- `src/yuantus/meta_engine/tests/test_approvals_router.py`
  - remove `approvals_router` import and registration from helper app setup.
- `src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py`
  - drop legacy shell from expected registration order.
  - add `test_app_does_not_register_legacy_approvals_router_shell`.
- `src/yuantus/meta_engine/tests/test_approval_category_router_contracts.py`
  - rename order test to assert category router is registered before request router.
- `src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py`
  - rename order test to assert request router is registered before ops router.
- `src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py`
  - rename registration-order test to verify ops router registration exists.
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
  - set `approvals_router.py` legacy state to `registered: False`.
- `docs/DEV_AND_VERIFICATION_APPROVALS_ROUTER_DECOMPOSITION_CLOSEOUT_20260424.md`
  - update narrative to reflect unregistered compatibility-shell behavior.

## Verification

Executed in `/Users/chouhua/Downloads/Github/Yuantus`:

- ` .venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_approval_category_router_contracts.py src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py src/yuantus/meta_engine/tests/test_approvals_router.py src/yuantus/meta_engine/tests/test_approvals_service.py src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py`
  - Result: **78 passed**
- `.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py`
  - Result: **1 passed**
- `.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/*router*contracts*.py`
  - Result: **402 passed in 61.12s**
- `.venv/bin/python -m py_compile src/yuantus/api/app.py src/yuantus/meta_engine/tests/test_approvals_router.py src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
  - Result: **passed**
- `git diff --check`
  - Result: **clean**

## Acceptance

- `/api/v1/approvals/*` routes are fully owned by:
  - `approval_category_router`
  - `approval_request_router`
  - `approval_ops_router`
- `approvals_router.py` remains as a zero-handler compatibility shell and is no longer imported/registered by production app startup.
- No runtime route or schema behavior change.

## Residual

- No additional code changes required for this step.
- Commit/PR split remains pending per closeout grouping workflow.
