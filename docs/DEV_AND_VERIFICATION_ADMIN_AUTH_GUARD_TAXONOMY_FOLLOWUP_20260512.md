# Admin Auth Guard Taxonomy Follow-up - Development and Verification

Date: 2026-05-12

## 1. Goal

Extend the access-guard taxonomy closeout to cover the remaining
`admin_auth.py` guard details for platform-admin and org-admin access.

This is a test and documentation follow-up. It does not change runtime behavior.

## 2. Scope

Modified:

- `src/yuantus/meta_engine/tests/test_access_guard_taxonomy_closeout_contracts.py`
- `docs/DEV_AND_VERIFICATION_ACCESS_GUARD_TAXONOMY_CLOSEOUT_20260512.md`
- `docs/DELIVERY_DOC_INDEX.md`

Added:

- `docs/DEV_AND_VERIFICATION_ADMIN_AUTH_GUARD_TAXONOMY_FOLLOWUP_20260512.md`

## 3. Taxonomy Extension

The existing closeout contract now also pins:

- `require_platform_admin` owns `Platform admin disabled`
- `require_platform_admin` owns `Platform admin required`
- `require_org_admin` owns `Org admin required`

The contract also asserts that `src/yuantus/api/routers/admin.py` does not own
any shared access-guard failure detail. It should import and use the shared
dependencies instead.

## 4. Non-Goals

- No runtime-code change.
- No admin route behavior change.
- No dependency-shape change.
- No conversion of platform-admin or org-admin semantics.
- No CAD, P3.4 cutover, scheduler, or new Phase work.

## 5. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_access_guard_taxonomy_closeout_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_access_guard_taxonomy_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_guard_consolidation_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_config_superuser_guard_contracts.py

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
- access taxonomy + admin auth + admin closeout + config superuser contracts:
  28 passed
- doc-index / CI list quartet: 5 passed
- boot check: `routes=676 middleware=4`
- `git diff --check`: clean

## 6. Review Checklist

- Confirm this PR is runtime-neutral.
- Confirm `require_platform_admin` keeps two distinct failure details.
- Confirm `require_org_admin` remains separate from platform-admin.
- Confirm `admin.py` does not regain local access-guard failure literals.
- Confirm doc-index ordering remains green.
