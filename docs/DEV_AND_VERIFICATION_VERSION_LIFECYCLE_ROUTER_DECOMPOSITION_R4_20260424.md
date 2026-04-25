# Version Router Decomposition R4: Lifecycle Routes

Date: 2026-04-24

## 1. Scope

R4 splits core Version lifecycle routes out of the legacy `version_router.py`
into `version_lifecycle_router.py`.

Moved routes:

- `POST /api/v1/versions/items/{item_id}/init`
- `POST /api/v1/versions/items/{item_id}/checkout`
- `POST /api/v1/versions/items/{item_id}/checkin`
- `POST /api/v1/versions/items/{item_id}/merge`
- `GET /api/v1/versions/compare`
- `POST /api/v1/versions/items/{item_id}/revise`
- `GET /api/v1/versions/items/{item_id}/history`
- `POST /api/v1/versions/items/{item_id}/branch`

## 2. Design

`version_lifecycle_router.py` owns the core VersionService write and compare
paths. The checkout doc-sync gate moves with checkout because it is part of the
write-time lifecycle policy, not a legacy read or file binding concern.

The application registration order is now:

1. `version_revision_router`
2. `version_iteration_router`
3. `version_file_router`
4. `version_lifecycle_router`
5. `version_router`

The remaining legacy `version_router.py` now contains only:

- `POST /api/v1/versions/{version_id}/effectivity`
- `GET /api/v1/versions/items/{item_id}/effective`
- `GET /api/v1/versions/items/{item_id}/tree`

## 3. Runtime Changes

- Added `src/yuantus/meta_engine/web/version_lifecycle_router.py`.
- Removed the same 8 lifecycle routes from `src/yuantus/meta_engine/web/version_router.py`.
- Registered `version_lifecycle_router` in `src/yuantus/api/app.py` before the legacy router.
- Updated lifecycle, merge, source checkout, and doc-sync gate tests to patch the new module.

No service logic, schema, migration, auth policy, or response shape was changed.

## 4. Contracts

Added `test_version_lifecycle_router_contracts.py` with route ownership
assertions:

- all 8 moved paths are owned by `yuantus.meta_engine.web.version_lifecycle_router`;
- legacy `version_router.py` no longer declares these paths;
- `version_lifecycle_router` is registered before `version_router`;
- each moved `(method, path)` is registered exactly once;
- all moved routes keep the `Versioning` tag;
- checkout still depends on `DocumentMultiSiteService.evaluate_checkout_sync_gate`.

The new contract test is registered in `.github/workflows/ci.yml`.

## 5. Verification

Py compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/version_lifecycle_router.py \
  src/yuantus/meta_engine/web/version_file_router.py \
  src/yuantus/meta_engine/web/version_iteration_router.py \
  src/yuantus/meta_engine/web/version_revision_router.py \
  src/yuantus/meta_engine/web/version_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Focused Version regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_file_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_iteration_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_iteration_router.py \
  src/yuantus/meta_engine/tests/test_version_revision_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_revision_router.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_advanced.py \
  src/yuantus/meta_engine/tests/test_version_checkout_checkin_router.py \
  src/yuantus/meta_engine/tests/test_version_merge_router.py \
  src/yuantus/meta_engine/tests/test_version_source_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `83 passed in 15.48s`.

## 6. Explicit Non-Goals

- Do not split effectivity/effective/tree in R4.
- Do not change `VersionService`.
- Do not change checkout doc-sync gate semantics.
- Do not delete `version_router.py`.

## 7. Next Slice

R5 should close the Version router decomposition by moving the remaining
effectivity/read routes to a small read/effectivity router or by converting
`version_router.py` into a compatibility shell.
