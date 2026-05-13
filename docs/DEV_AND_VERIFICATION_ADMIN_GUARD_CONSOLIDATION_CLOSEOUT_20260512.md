# Admin Guard Consolidation Closeout - Development and Verification

Date: 2026-05-12

## 1. Goal

Close the admin guard consolidation sequence that landed through:

- `docs/DEV_AND_VERIFICATION_ADMIN_AUTH_GUARD_CONSOLIDATION_20260512.md`
- `docs/DEV_AND_VERIFICATION_ADMIN_PERMISSION_GUARD_FOLLOWUP_20260512.md`
- `docs/DEV_AND_VERIFICATION_ADMIN_PERMISSION_ROUTER_GUARDS_20260512.md`
- `docs/DEV_AND_VERIFICATION_MANUFACTURING_ADMIN_GUARD_FOLLOWUP_20260512.md`
- `docs/DEV_AND_VERIFICATION_DEDUP_ADMIN_GUARD_FOLLOWUP_20260512.md`

This closeout adds no runtime behavior. It adds a CI contract that prevents the
old local admin-helper pattern from returning.

## 2. Runtime State

The shared admin guard taxonomy is now:

| Helper | Failure detail | Intended surface |
| --- | --- | --- |
| `require_admin_user` | `Admin role required` | dependency-style admin endpoints and manufacturing direct calls |
| `require_admin_permission` | `Admin permission required` | e-sign, release-readiness, release-orchestration, item-cockpit direct calls |
| `require_admin_access` | `Admin required` | dedup direct calls |

All three helpers use `user_has_admin_role(user)`.

## 3. Contract Added

Added:

- `src/yuantus/meta_engine/tests/test_admin_guard_consolidation_closeout_contracts.py`

The contract verifies:

- every Python file under `src/yuantus/meta_engine/web` has no local
  `_ensure_admin` function
- the three admin failure details are no longer owned by web routers
- `auth.py` owns the three shared helper/detail pairs
- this closeout contract is wired into CI
- this MD is indexed in `docs/DELIVERY_DOC_INDEX.md`

## 4. Non-Goals

- No route, request, response, service, transaction, or dependency-shape change.
- No new admin semantics.
- No merge of the three distinct failure details.
- No Phase 5, P3.4 cutover, CAD, scheduler, Dedup Vision, or circuit breaker work.

## 5. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_admin_guard_consolidation_closeout_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_admin_guard_consolidation_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_guard_followup_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_dedup_admin_guard_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_admin_guard_consolidation_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

.venv/bin/python -c "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

Results:

- py_compile: passed
- admin guard closeout plus admin guard family contracts: 35 passed
- closeout contract plus router-decomposition portfolio regression: 9 passed
- doc-index and CI-list contracts: 5 passed
- app boot: `routes=676 middleware=4`
- git diff --check: clean

## 6. Review Checklist

- Confirm this PR has no runtime-code changes.
- Confirm the closeout contract scans all `meta_engine/web/*.py` files.
- Confirm `Admin role required`, `Admin permission required`, and
  `Admin required` remain distinct.
- Confirm CI list ordering and doc-index ordering stay green.
