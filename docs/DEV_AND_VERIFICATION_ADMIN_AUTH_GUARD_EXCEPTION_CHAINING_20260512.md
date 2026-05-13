# Admin Auth Guard Exception Chaining - Development and Verification

Date: 2026-05-12

## 1. Goal

Preserve the original exception cause when `require_org_admin` converts an
identity-store membership lookup failure into the existing API-facing
`403 Org admin required` response.

This is a narrow guard-quality fix following the admin-auth taxonomy closeout.

## 2. Scope

Modified:

- `src/yuantus/api/dependencies/admin_auth.py`
- `src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `docs/DEV_AND_VERIFICATION_ADMIN_AUTH_GUARD_EXCEPTION_CHAINING_20260512.md`

## 3. Behavior

The API-visible behavior is unchanged:

```text
403 Org admin required
```

The internal exception chain now preserves the original membership lookup
failure via `raise HTTPException(...) from exc`.

## 4. Contract Coverage

The existing admin-auth guard contract now asserts that the lookup-failure path
keeps a `RuntimeError` as `HTTPException.__cause__`. This catches future
regressions back to a bare `raise HTTPException(...)`.

## 5. Non-Goals

- No route behavior change.
- No status-code or response-body change.
- No role semantics change.
- No platform-admin, superuser, or admin-role helper change.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 6. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/api/dependencies/admin_auth.py \
  src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_access_guard_taxonomy_closeout_contracts.py

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
- admin auth + access taxonomy contracts: 18 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 7. Review Checklist

- Confirm API-visible detail remains `Org admin required`.
- Confirm `require_org_admin` uses `from exc` on membership lookup failures.
- Confirm no platform-admin or superuser behavior changed.
- Confirm doc-index ordering remains green.
