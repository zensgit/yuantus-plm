# Admin Permission Guard Follow-Up - Development and Verification

Date: 2026-05-12

## 1. Goal

Finish the bounded admin-guard cleanup that was explicitly left out of
`docs/DEV_AND_VERIFICATION_REQUIRE_ADMIN_DEPENDENCY_DEDUP_20260421.md`: move
the local `_ensure_admin` checks in `esign_router.py` and
`release_readiness_router.py` onto a shared helper.

This is an independent triggered taskbook outside the blocked six-phase arc. It
does not start Phase 5, P3.4 cutover, CAD work, scheduler work, or a broad RBAC
redesign.

## 2. Previous State

Two routers still carried local admin-permission checks:

- `src/yuantus/meta_engine/web/esign_router.py`
- `src/yuantus/meta_engine/web/release_readiness_router.py`

Both used the same user-facing failure detail:

```text
Admin permission required
```

That differs from `require_admin_user`, which intentionally returns:

```text
Admin role required
```

Using `require_admin_user` directly would have changed the existing e-sign and
release-readiness API error body. This follow-up therefore adds a separate
shared direct-call helper that preserves the established detail string without
adding a new FastAPI dependency edge.

## 3. Implementation

Added `require_admin_permission` in
`src/yuantus/api/dependencies/auth.py`.

The helper:

- reuses the existing `user_has_admin_role(user)` normalizer
- allows admin role, superuser role, and `is_superuser=True`
- rejects non-admin users with `403 Admin permission required`

Updated:

- `src/yuantus/meta_engine/web/esign_router.py`
- `src/yuantus/meta_engine/web/release_readiness_router.py`

Both routers now import `require_admin_permission` and no longer define local
`_ensure_admin`.

## 4. Contract Coverage

Added `src/yuantus/meta_engine/tests/test_admin_permission_guard_followup_contracts.py`.

The contract covers:

- shared helper allows normalized admin role
- shared helper allows `is_superuser=True`
- shared helper rejects viewer with `403 Admin permission required`
- both routers import the shared helper
- both routers no longer define local `_ensure_admin`
- CI wiring and doc-index registration

Existing endpoint tests still cover the user-facing paths:

- `test_esign_router_permissions.py`
- `test_release_readiness_router.py`
- `test_release_readiness_export_bundles.py`

## 5. CI Registration

`.github/workflows/ci.yml` now includes:

```text
src/yuantus/meta_engine/tests/test_admin_permission_guard_followup_contracts.py
```

`docs/DELIVERY_DOC_INDEX.md` now includes this development and verification
record in alphabetical order.

## 6. Non-Goals

- No change to route paths, request bodies, or response models.
- No change to the e-sign/release-readiness 403 detail string.
- No conversion of unrelated local `_ensure_admin` helpers in manufacturing,
  item cockpit, release orchestration, or dedup routers.
- No Phase 5 implementation.
- No P3.4 evidence synthesis or cutover.
- No CAD plugin changes.
- No scheduler or production rehearsal work.

## 7. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/api/dependencies/auth.py \
  src/yuantus/meta_engine/web/esign_router.py \
  src/yuantus/meta_engine/web/release_readiness_router.py \
  src/yuantus/meta_engine/tests/test_admin_permission_guard_followup_contracts.py

YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest \
  src/yuantus/meta_engine/tests/test_admin_permission_guard_followup_contracts.py \
  src/yuantus/meta_engine/tests/test_admin_dependency_dedup.py \
  src/yuantus/meta_engine/tests/test_esign_router_permissions.py \
  src/yuantus/meta_engine/tests/test_release_readiness_router.py \
  src/yuantus/meta_engine/tests/test_release_readiness_export_bundles.py

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
- admin permission + e-sign + release-readiness focused suite: 25 passed
- doc-index + CI list contracts: 5 passed
- app boot: routes=676, middleware=4
- git diff --check: clean

The focused route suite uses `YUANTUS_AUTH_MODE=optional` so the tests exercise
their existing `get_current_user` dependency overrides instead of being
short-circuited by global `AuthEnforcementMiddleware` before route dispatch.

## 8. Reviewer Checklist

- Confirm `require_admin_permission` preserves `403 Admin permission required`.
- Confirm e-sign and release-readiness routers no longer define `_ensure_admin`.
- Confirm route signatures and paths are unchanged.
- Confirm unrelated local `_ensure_admin` helpers are intentionally untouched.
- Confirm the new contract is included in CI.
- Confirm doc-index sorting, completeness, and references remain green.
