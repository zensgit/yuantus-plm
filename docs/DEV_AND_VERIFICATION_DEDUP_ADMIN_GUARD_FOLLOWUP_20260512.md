# Dedup Admin Guard Follow-up - Development and Verification

Date: 2026-05-12

## 1. Goal

Finish the admin guard consolidation line by moving `dedup_router.py`, the last
router with a local `_ensure_admin` helper, onto a shared auth dependency helper
without changing its existing user-facing failure detail.

This is a narrow cleanup. It does not start Phase 5, P3.4 cutover, CAD work,
scheduler work, or a broader RBAC redesign.

## 2. Scope

Updated runtime files:

- `src/yuantus/api/dependencies/auth.py`
- `src/yuantus/meta_engine/web/dedup_router.py`

`auth.py` now exposes `require_admin_access(user)`, a direct-call helper that
uses the shared admin-role predicate and rejects non-admin users with:

```text
403 Admin required
```

`dedup_router.py` now imports that helper and replaces all 15 local
`_ensure_admin(user)` calls with `require_admin_access(user)`.

## 3. Behavior Preserved

The dedup route family keeps its existing detail string:

```text
Admin required
```

The guard uses the same normalized shared admin predicate as
`require_admin_user` and `require_admin_permission`:

- `admin` role is allowed
- `superuser` role is allowed
- `is_superuser=True` is allowed
- role values are stripped and compared case-insensitively by
  `user_has_admin_role`

The helper is called after each route's existing `get_current_user` dependency
resolves. It is intentionally not converted to a new `Depends(...)` edge, so the
route dependency shape remains stable.

## 4. Contract Coverage

Added `src/yuantus/meta_engine/tests/test_dedup_admin_guard_contracts.py`.

The contract verifies:

- `require_admin_access` allows admin users and superuser flag users
- non-admin users receive `403 Admin required`
- `dedup_router.py` imports and direct-calls `require_admin_access(user)`
  exactly 15 times
- `dedup_router.py` no longer defines local `_ensure_admin`
- `dedup_router.py` no longer carries a local `Admin required` literal
- `auth.py` owns the `Admin required` detail string
- CI wiring and doc-index registration

The previous admin-permission and manufacturing guard contracts were updated so
their dedup assertions now point at the shared dedup-specific helper instead of
expecting a remaining local helper.

## 5. Non-Goals

- No route path, request, response, service, or transaction change.
- No conversion to `Depends(require_admin_access)`.
- No change to `require_admin_user` (`Admin role required`).
- No change to `require_admin_permission` (`Admin permission required`).
- No dedup service, Dedup Vision, circuit breaker, scheduler, CAD, or Phase 5
  changes.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/api/dependencies/auth.py \
  src/yuantus/meta_engine/web/dedup_router.py \
  src/yuantus/meta_engine/tests/test_dedup_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py

YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dedup_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_dependency_dedup.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_dedup_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py \
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
- dedup/admin/manufacturing guard contract suite: 20 passed
- guard contracts plus router-decomposition portfolio regression: 18 passed
- doc-index and CI-list contracts: 5 passed
- app boot: `routes=676 middleware=4`
- git diff --check: clean

## 7. Review Checklist

- Confirm `dedup_router.py` has no local `_ensure_admin` function.
- Confirm all 15 previous guard calls use `require_admin_access(user)`.
- Confirm `Admin required` remains owned by `auth.py`.
- Confirm `require_admin_user` and `require_admin_permission` details are not
  changed.
- Confirm CI includes the new contract file without a `*_router_contracts.py`
  filename that would be picked up by router portfolio discovery.
