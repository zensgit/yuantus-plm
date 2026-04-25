# DEV_AND_VERIFICATION_APPROVALS_EXPORT_GUARD_TRANSACTIONAL_FOLLOWUP_20260426

## Scope
- Follow-up for PR #398 approvals cleanup.
- Focused on two follow-up items:
  - CSV/Markdown export payload type guard at router boundary.
  - Transactional dedup for approval write endpoints (`create_approval_request`, `transition_approval_request`, `create_approval_category`).

## Changes
- Added `src/yuantus/meta_engine/web/_approval_write_transaction.py` with `transactional_write(db)` context manager:
  - commits on success
  - rollbacks and maps `ValueError` to `HTTP 400`
  - rollbacks and re-raises other exceptions.
- Rewired write endpoints to use `transactional_write(db)`:
  - `approval_request_router.py`: `create_approval_request`, `transition_approval_request`
  - `approval_category_router.py`: `create_approval_category`
- Added payload type hardening for export helpers:
  - `approval_request_router.py::_export_response`
  - `approval_ops_router.py::_export_response`
  - For `csv` and `markdown`, non-`str` payload now returns `HTTP 500` with clear detail message.
- Added regression tests:
  - `src/yuantus/meta_engine/tests/test_approvals_router.py`:
    - 2 transition/create/category rollback assertions
    - 4 export contract violation tests for `csv`/`markdown` payload type mismatch

## Verification
- `PYTHONPATH=src .venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_approvals_router.py src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py src/yuantus/meta_engine/tests/test_approval_category_router_contracts.py`
  - `42 passed in 4.80s`
- `PYTHONPATH=src .venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
  - `11 passed in 2.56s`
- `PYTHONPATH=src .venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py`
  - `4 passed in 0.03s`
- `PYTHONPATH=src .venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_ci_contracts_doc_index_sorting.py`
  - `1 passed in 0.01s`
- `PYTHONPATH=src .venv/bin/python -m py_compile` on:
  - `src/yuantus/meta_engine/web/approval_request_router.py`
  - `src/yuantus/meta_engine/web/approval_ops_router.py`
  - `src/yuantus/meta_engine/web/approval_category_router.py`
  - `src/yuantus/meta_engine/web/_approval_write_transaction.py`
  - `src/yuantus/meta_engine/tests/test_approvals_router.py`
- `git diff --check`
  - clean

## Result
- Follow-up scope complete on branch `followup/approvals-export-type-and-transactional-20260426`.
- No remaining known blockers for this scope.
