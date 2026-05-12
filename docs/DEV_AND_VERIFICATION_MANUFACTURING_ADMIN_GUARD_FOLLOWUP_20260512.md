# Manufacturing Admin Guard Follow-up - Development and Verification

Date: 2026-05-12

## 1. Goal

Continue the admin guard consolidation after
`docs/DEV_AND_VERIFICATION_ADMIN_PERMISSION_ROUTER_GUARDS_20260512.md` by
moving `manufacturing_router.py` off its local `_ensure_admin` helper and onto
the existing shared `require_admin_user(user)` helper.

This is a narrow cleanup. It does not start Phase 5, P3.4 cutover, CAD work,
scheduler work, or a broader RBAC redesign.

## 2. Scope

Updated router:

- `src/yuantus/meta_engine/web/manufacturing_router.py`

The router had 16 direct calls to a local `_ensure_admin(user)` helper. Those
calls now direct-call `require_admin_user(user)` after the route's existing
`get_current_user` dependency resolves.

## 3. Behavior Preserved

The migrated user-facing contract remains:

```text
403 Admin role required
```

`require_admin_user` allows:

- `admin` role
- `superuser` role
- `is_superuser=True`

It rejects non-admin users with `403 Admin role required`, matching the
manufacturing route tests and the existing shared dependency contract.

## 4. Non-Goals

- No route path, request, response, service, or transaction change.
- No conversion to `Depends(require_admin_user)`; the route dependency shape
  remains `Depends(get_current_user)` plus an explicit guard call.
- No change to `dedup_router.py`; it still returns `403 Admin required` and
  remains intentionally distinct.
- No change to `Admin permission required` routers; those were handled in the
  previous admin-permission cleanup.

## 5. Contract Coverage

Added `src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py`.

The contract verifies:

- manufacturing imports and calls `require_admin_user(user)` exactly 16 times
- manufacturing no longer defines local `_ensure_admin`
- manufacturing no longer carries a local `Admin role required` literal
- `require_admin_user` remains the owner of the `Admin role required` detail
- `dedup_router.py` remains out of scope with `Admin required`
- CI wiring and doc-index registration

The previous admin-permission contract was narrowed so it only keeps `dedup` as
the remaining permission-scope exception.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/manufacturing_router.py \
  src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py

YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_dependency_dedup.py \
  src/yuantus/meta_engine/tests/test_manufacturing_mbom_router.py \
  src/yuantus/meta_engine/tests/test_manufacturing_routing_router.py \
  src/yuantus/meta_engine/tests/test_manufacturing_workcenter_router.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_manufacturing_admin_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py \
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
- manufacturing/admin/dedup focused suite: 41 passed
- guard contracts plus router-decomposition portfolio regression: 12 passed
- doc-index and CI-list contracts: 5 passed
- app boot: `routes=676 middleware=4`
- git diff --check: clean

## 7. Review Checklist

- Confirm `manufacturing_router.py` has no local `_ensure_admin` function.
- Confirm all 16 previous guard calls use `require_admin_user(user)`.
- Confirm endpoint tests still assert `Admin role required`.
- Confirm `dedup_router.py` stays unchanged because its detail is `Admin required`.
- Confirm CI includes the new contract file without a `*_router_contracts.py`
  filename that would be picked up by router portfolio discovery.
