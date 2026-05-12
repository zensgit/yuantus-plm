# Admin Auth Guard Consolidation - Development and Verification

Date: 2026-05-12

## 1. Goal

Consolidate the admin router's local authorization guards into a shared dependency module without changing route behavior.

This is intentionally a small refactor slice. It does not start Phase 3 cutover work, CAD work, scheduler work, or a broader admin-router decomposition.

## 2. Previous State

`src/yuantus/api/routers/admin.py` defined four auth-related helpers locally:

- `_get_org`
- `require_superuser`
- `require_platform_admin`
- `require_org_admin`

Those helpers were route-owner logic embedded inside a large router module. The behavior was valid, but the placement made reuse and focused contract coverage harder.

## 3. Implementation

Added `src/yuantus/api/dependencies/admin_auth.py` and moved the admin guards there.

The admin router now imports:

- `_get_org`
- `require_superuser`
- `require_platform_admin`
- `require_org_admin`

The router no longer imports `get_current_identity` directly and no longer defines the guard functions locally.

## 4. Behavior Preserved

The refactor preserves the existing failure semantics:

- non-superuser access to superuser endpoints returns `403 Superuser required`
- disabled platform-admin mode returns `403 Platform admin disabled`
- wrong platform tenant or non-superuser platform access returns `403 Platform admin required`
- missing org returns `404 Org not found`
- org membership lookup failure returns `403 Org admin required`
- org roles remain exact-match only: `admin` and `org_admin`

Superusers still bypass membership-role lookup only after org existence is verified.

## 5. Contract Coverage

Added `src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py`.

The contract covers:

- `require_superuser` allow and reject paths
- `require_platform_admin` disabled, wrong-tenant, and allow paths
- `require_org_admin` superuser, `admin`, `org_admin`, non-admin, and lookup-failure paths
- admin router source shape: guards must be imported from `yuantus.api.dependencies.admin_auth`, not locally redefined
- CI wiring and doc-index registration

## 6. CI Registration

`.github/workflows/ci.yml` now includes:

```text
src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py
```

`docs/DELIVERY_DOC_INDEX.md` now includes this development and verification record in alphabetical order.

## 7. Non-Goals

- No route registration change
- No endpoint behavior change
- No role semantics change
- No service-layer redesign
- No admin router decomposition beyond moving the four auth helpers
- No CAD material-sync work
- No Phase 3 tenant cutover work
- No scheduler or background-job work

## 8. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/api/dependencies/admin_auth.py \
  src/yuantus/api/routers/admin.py \
  src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py

.venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_admin_auth_guard_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_dependency_dedup.py

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
- admin auth guard + existing admin dependency focused suite: 19 passed
- doc-index + CI list contracts: 5 passed
- app boot: routes=676, middleware=4
- git diff --check: clean

Note: `/usr/bin/python3` is Python 3.9.6 in this local checkout and cannot collect one existing Python 3.10+ annotation in `search_router.py`. The validated project interpreter for this run was `.venv/bin/python` (Python 3.11.15).

## 9. Review Checklist

- Confirm `admin.py` imports guards from `yuantus.api.dependencies.admin_auth`.
- Confirm `admin.py` no longer defines `_get_org`, `require_superuser`, `require_platform_admin`, or `require_org_admin`.
- Confirm all prior HTTP status and detail strings are preserved.
- Confirm role semantics remain exact-match `admin` / `org_admin`.
- Confirm the new contract is included in CI.
- Confirm doc-index sorting, completeness, and references remain green.
