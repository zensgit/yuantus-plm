# Version Router Decomposition R3: File Routes

Date: 2026-04-24

## 1. Scope

R3 splits the file-aware Version API routes out of the legacy `version_router.py`
into `version_file_router.py`.

Moved routes:

- `GET /api/v1/versions/{version_id}/detail`
- `POST /api/v1/versions/{version_id}/files`
- `DELETE /api/v1/versions/{version_id}/files/{file_id}`
- `GET /api/v1/versions/{version_id}/files`
- `POST /api/v1/versions/{version_id}/files/{file_id}/checkout`
- `POST /api/v1/versions/{version_id}/files/{file_id}/undo-checkout`
- `GET /api/v1/versions/{version_id}/files/{file_id}/lock`
- `PUT /api/v1/versions/{version_id}/files/primary`
- `PUT /api/v1/versions/{version_id}/thumbnail`
- `GET /api/v1/versions/compare-full`
- `GET /api/v1/versions/items/{item_id}/tree-full`

## 2. Design

`version_file_router.py` owns VersionFileService integration, request models, file
editability checks, file error mapping, and the file-aware compare/tree read
routes. The legacy `version_router.py` keeps only non-file lifecycle and
effectivity/read routes for later R4/R5 decomposition.

The application registration order is:

1. `version_revision_router`
2. `version_iteration_router`
3. `version_file_router`
4. `version_router`

This preserves the public `/api/v1/versions/*` surface while giving split
routers ownership before the legacy router is included.

## 3. Runtime Changes

- Added `src/yuantus/meta_engine/web/version_file_router.py`.
- Removed the same 11 file routes from `src/yuantus/meta_engine/web/version_router.py`.
- Registered `version_file_router` in `src/yuantus/api/app.py` before the legacy router.
- Updated existing file checkout tests to patch `version_file_router.VersionFileService`.
- Added behavior coverage for detail, thumbnail, full compare, and full tree routes.

No service logic, schema, migration, auth policy, or response shape was changed.

## 4. Contracts

Added `test_version_file_router_contracts.py` with route ownership assertions:

- all 11 moved paths are owned by `yuantus.meta_engine.web.version_file_router`;
- legacy `version_router.py` no longer declares these paths;
- `version_file_router` is registered before `version_router`;
- each moved `(method, path)` is registered exactly once;
- all moved routes keep the `Versioning` tag;
- `compare-full` and `tree-full` remain in the file router source.

The new contract test is registered in `.github/workflows/ci.yml`.

## 5. Verification

Py compile:

```bash
.venv/bin/python -m py_compile \
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

Result: `77 passed in 14.71s`.

Full router contract sweep:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
```

Result: `314 passed in 46.49s`.

Doc index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `3 passed in 0.03s`.

Diff whitespace check:

```bash
git diff --check
```

Result: passed.

## 6. Explicit Non-Goals

- Do not split lifecycle checkout/checkin/merge/revise routes in R3.
- Do not split effectivity/effective/tree routes in R3.
- Do not change `VersionService` or `VersionFileService`.
- Do not change response payloads or auth semantics.
- Do not delete `version_router.py`.

## 7. Next Slice

R4 should split the core lifecycle routes into `version_lifecycle_router.py`.
Recommended route set:

- `POST /items/{item_id}/init`
- `POST /items/{item_id}/checkout`
- `POST /items/{item_id}/checkin`
- `POST /items/{item_id}/merge`
- `GET /compare`
- `POST /items/{item_id}/revise`
- `GET /items/{item_id}/history`
- `POST /items/{item_id}/branch`

The checkout doc-sync gate should move with lifecycle because it is part of the
core checkout path.
