# Config Superuser Guard - Development and Verification

Date: 2026-05-12

## 1. Goal

Continue the guard consolidation work after the admin guard closeout by moving
`config_router.py` off its local `_ensure_superuser` helper and onto the shared
`require_superuser` helper.

This is a narrow cleanup. It does not start Phase 5, P3.4 cutover, CAD work,
scheduler work, or a broader RBAC redesign.

## 2. Scope

Updated runtime files:

- `src/yuantus/api/dependencies/admin_auth.py`
- `src/yuantus/meta_engine/web/config_router.py`

`require_superuser` now accepts either an `Identity` dependency value or a
direct-call `CurrentUser`. The check still only depends on `is_superuser` and
preserves the existing failure detail:

```text
403 Superuser required
```

`config_router.py` keeps its existing `Depends(get_current_user)` route shape
and direct-calls `require_superuser(user)` at the 9 existing write endpoints.

## 3. Behavior Preserved

- superuser users are allowed
- non-superuser users receive `403 Superuser required`
- route paths, request models, response models, services, and transactions are
  unchanged
- config read endpoints remain unchanged

## 4. Contract Coverage

Added:

- `src/yuantus/meta_engine/tests/test_config_superuser_guard_contracts.py`

The contract verifies:

- `require_superuser` accepts direct-call `CurrentUser` values
- non-superuser `CurrentUser` values still receive `403 Superuser required`
- `config_router.py` direct-calls `require_superuser(user)` exactly 9 times
- `config_router.py` no longer defines local `_ensure_superuser`
- `config_router.py` no longer carries a local `Superuser required` literal
- a real config write route still rejects non-superuser users
- CI wiring and doc-index registration

## 5. Non-Goals

- No conversion to `Depends(require_superuser)`.
- No change to platform-admin or org-admin guards.
- No change to `require_admin_user`, `require_admin_permission`, or
  `require_admin_access`.
- No config service behavior change.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/api/dependencies/admin_auth.py \
  src/yuantus/meta_engine/web/config_router.py \
  src/yuantus/meta_engine/tests/test_config_superuser_guard_contracts.py

YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_config_superuser_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_config_superuser_guard_contracts.py \
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

- `py_compile`: passed
- config superuser + admin auth guard focused suite: 18 passed
- config superuser + admin guard closeout + router portfolio suite: 15 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm `config_router.py` has no local `_ensure_superuser` function.
- Confirm all 9 previous guard calls use `require_superuser(user)`.
- Confirm `Superuser required` remains owned by `admin_auth.py`.
- Confirm route dependency shape remains `get_current_user`.
- Confirm CI list ordering and doc-index ordering stay green.
