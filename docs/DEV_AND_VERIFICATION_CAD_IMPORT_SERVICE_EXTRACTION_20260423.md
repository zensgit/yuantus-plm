# DEV AND VERIFICATION: CadImportService Extraction

Date: 2026-04-23

## 1. Goal

Extract CAD import business logic from `cad_import_router.py` into `CadImportService` while preserving the public `POST /api/v1/cad/import` API contract.

## 2. Runtime Changes

Added:

- `src/yuantus/meta_engine/services/cad_import_service.py`

Changed:

- `src/yuantus/meta_engine/web/cad_import_router.py`
- `src/yuantus/meta_engine/tests/test_cad_import_service.py`
- `src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py`
- `src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_ci_contracts_cad_import_dedup_index.py`

Documentation:

- `docs/DEV_AND_VERIFICATION_CAD_IMPORT_SERVICE_EXTRACTION_20260423.md`
- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260422.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The router remains the HTTP boundary:

- FastAPI form declarations.
- `UploadFile.read()`.
- Dependency injection.
- `CadImportError` to `HTTPException` mapping.
- `X-Quota-Warning` header application.
- `CadImportResponse` response assembly.
- CAD viewer URL construction through `Request.url_for()`.

The new service owns:

- Upload validation.
- Checksum and duplicate file lookup.
- Missing storage repair for duplicate files.
- New-file quota evaluation.
- CAD metadata / connector resolution.
- Auto Part create/update.
- Item-file link create/update.
- Current-version file editability guards.
- Active job quota evaluation.
- CAD preview / geometry / extract / BOM / dedup / ML job enqueue payloads.

## 4. Interface

New service data objects:

- `CadImportRequest`
- `CadImportResult`
- `CadImportJobResult`

New service exceptions:

- `CadImportError`
- `CadImportValidationError`
- `CadImportConflictError`
- `CadImportQuotaError`
- `CadImportUpstreamError`

The router catches `CadImportError` and maps `status_code` / `detail` directly to `HTTPException`, preserving the existing HTTP contract.

## 5. Behavior Preserved

- `POST /api/v1/cad/import` path and response model unchanged.
- Empty file remains 400.
- File size / extension validation remains 413 / 415.
- Hard quota remains 429 with `QUOTA_EXCEEDED` payload.
- Soft quota warnings still use `X-Quota-Warning`.
- Duplicate missing-storage repair still checks current-version file locks before upload.
- `create_bom_job=True` still requires `item_id` or `auto_create_part`.
- Auto Part create/update behavior remains in the same sequence.
- Existing and new item-file links still pass current-version editability guards.
- Job payloads still include file, source path, CAD metadata, tenant, org, user, roles, auth, and optional `item_id`.
- Dedup job still carries `mode`, `user_name`, and `index`.

## 6. Tests Added / Updated

Added `test_cad_import_service.py` with 11 service-level cases:

- hard new-file quota maps to `CadImportQuotaError`;
- duplicate missing-storage repair calls lock guard before upload;
- BOM job without item or auto Part raises 400-equivalent validation;
- auto Part update path;
- auto Part create path;
- existing item-file link role update checks old and new roles;
- new item-file link checks editability before insert;
- active job quota blocks enqueue;
- normal enqueue payload includes scope/auth/CAD metadata/item id;
- dedup payload preserves `mode`, `user_name`, and `index`;
- file lock conflict maps to `CadImportConflictError`.

Updated existing tests:

- `test_cad_import_lock_guards.py` patch paths now target `cad_import_service`.
- `test_ci_contracts_cad_import_dedup_index.py` verifies the public form field remains in the router and the payload flag lives in the service.
- `test_cad_import_router_contracts.py` adds a static contract that the router no longer directly imports core business services.

## 7. Verification

Compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/cad_import_router.py \
  src/yuantus/meta_engine/services/cad_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_import_service.py
```

Result: passed.

CAD import focused:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py \
  src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_import_dedup_index.py
```

Result: `20 passed`.

CAD adjacent:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_import_service.py \
  src/yuantus/meta_engine/tests/test_cad_import_lock_guards.py \
  src/yuantus/meta_engine/tests/test_cad_import_router_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_cad_import_dedup_index.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_status_router.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_checkin_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_connectors_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_file_data_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_mesh_stats_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_properties_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_review_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_sync_template_router_contracts.py \
  src/yuantus/meta_engine/tests/test_cad_view_state_router_contracts.py
```

Result: `54 passed`.

Doc contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `3 passed`.

Whitespace:

```bash
git diff --check
```

Result: passed.

## 8. Non-Goals

- No schema or migration changes.
- No public API route or response field changes.
- No worker task type or priority changes.
- No CAD backend profile, FreeCAD, STEP/IGES, scheduler, UI, or shared-dev 142 changes.
- No file storage layout change.

## 9. Status

Implementation and focused verification are complete.
