# Admin Permission Router Guards - Development and Verification

Date: 2026-05-12

## 1. Goal

Continue the admin-permission guard cleanup after
`docs/DEV_AND_VERIFICATION_ADMIN_PERMISSION_GUARD_FOLLOWUP_20260512.md` by
moving two more local `Admin permission required` guards onto the shared
`require_admin_permission(user)` helper.

This is an independent triggered cleanup outside the blocked six-phase arc. It
does not start Phase 5, P3.4 cutover, CAD work, scheduler work, or broad RBAC
redesign.

## 2. Scope

Updated routers:

- `src/yuantus/meta_engine/web/release_orchestration_router.py`
- `src/yuantus/meta_engine/web/item_cockpit_router.py`

Both routers used local `_ensure_admin` helpers with the same user-facing
failure detail:

```text
Admin permission required
```

Both now import and direct-call `require_admin_permission(user)`.

## 3. Behavior Preserved

The shared helper preserves the existing user-facing contract:

- admin role is allowed
- superuser role is allowed
- `is_superuser=True` is allowed
- non-admin users receive `403 Admin permission required`

The helper is called after each route's existing `get_current_user` dependency
resolves. It is intentionally not used as a new `Depends(...)` edge, so existing
test overrides and route dependency shapes remain stable.

## 4. Contract Coverage

Added `src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py`.

The contract covers:

- release-orchestration imports the shared helper and no longer defines local
  `_ensure_admin`
- item-cockpit imports the shared helper and no longer defines local
  `_ensure_admin`
- both routers no longer carry local `Admin permission required` literals
- `dedup_router.py` remains out of scope because its current user-facing detail
  is `Admin required`
- `manufacturing_router.py` remains out of scope because its current
  user-facing detail is `Admin role required`
- CI wiring and doc-index registration

Existing endpoint tests cover route behavior:

- `test_release_orchestration_router.py`
- `test_item_cockpit_router.py`

## 5. CI Registration

`.github/workflows/ci.yml` now includes:

```text
src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py
```

`docs/DELIVERY_DOC_INDEX.md` includes this document in alphabetical order.

## 6. Non-Goals

- No change to route paths, request bodies, response models, or service calls.
- No change to `Admin permission required` behavior.
- No conversion of `dedup_router.py`; it returns `Admin required`.
- No conversion of `manufacturing_router.py`; it returns `Admin role required`.
- No Phase 5 implementation.
- No P3.4 evidence synthesis or cutover.
- No CAD plugin changes.
- No scheduler or production rehearsal work.

## 7. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/release_orchestration_router.py \
  src/yuantus/meta_engine/web/item_cockpit_router.py \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py

YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_admin_permission_shared_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_release_orchestration_router.py \
  src/yuantus/meta_engine/tests/test_item_cockpit_router.py

.venv/bin/python -m pytest \
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
- release-orchestration + item-cockpit focused suite: 21 passed
- shared-guard contract + router-decomposition portfolio regression: 8 passed
- doc-index + CI list contracts: 5 passed
- app boot: routes=676, middleware=4
- git diff --check: clean

CI remediation note: the contract file is named
`test_admin_permission_shared_guard_contracts.py`, not
`test_admin_permission_router_guard_contracts.py`, so it does not match the
router-decomposition portfolio's router-contract file discovery pattern.

## 8. Reviewer Checklist

- Confirm only release-orchestration and item-cockpit move to the shared helper.
- Confirm `dedup_router.py` and `manufacturing_router.py` remain intentionally
  unchanged because their detail strings differ.
- Confirm route dependency shape remains `get_current_user` plus direct helper
  call.
- Confirm CI includes the new contract.
- Confirm doc-index sorting, completeness, and references stay green.
