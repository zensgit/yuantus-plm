# Claude Task - File Router Decomposition

Date: 2026-04-23

## 1. Goal

Reduce `src/yuantus/meta_engine/web/file_router.py` by splitting cohesive route families into dedicated routers while preserving the public `/api/v1/file/*` API surface.

This task starts a new backend-hotspot reduction cycle after the previous next-cycle plan was closed.

## 2. R1 Scope

R1 moves only file conversion routes into `file_conversion_router.py`:

- `GET /file/supported-formats`
- `GET /file/{file_id}/conversion_summary`
- `POST /file/{file_id}/convert`
- `GET /file/conversion/{job_id}`
- `GET /file/conversions/pending`
- `POST /file/conversions/process`
- `POST /file/process_cad`

Public paths, methods, response models, status codes, and legacy headers must remain unchanged.

## 3. R1 Required Changes

- Add `src/yuantus/meta_engine/web/file_conversion_router.py`.
- Register `file_conversion_router` before legacy `file_router` in `src/yuantus/api/app.py`.
- Remove moved route decorators from `file_router.py`.
- Keep upload preview queueing functional by sharing the conversion job enqueue helper.
- Add `test_file_conversion_router_contracts.py`.
- Update existing file conversion tests to patch the new module path.
- Register the new contract test in `.github/workflows/ci.yml`.
- Add `DEV_AND_VERIFICATION_FILE_ROUTER_DECOMPOSITION_R1_CONVERSION_20260423.md`.
- Register delivery docs in `docs/DELIVERY_DOC_INDEX.md`.

## 4. R1 Non-Goals

- Do not move upload, attachment, metadata, download, preview, geometry, CAD artifact, or viewer-readiness routes.
- Do not change `FileService`, `CADConverterService`, `JobService`, `JobWorker`, schema, settings, or migrations.
- Do not change `/api/v1/file/*` public behavior.
- Do not run shared-dev `142` bootstrap or scheduler activation.
- Do not delete `file_router.py`.

## 5. R2+ Sketch

R2 should move CAD/viewer read routes.

R3 should move upload and item attachment routes.

Do not implement R2 or R3 until R1 is merged and reviewed.

## 6. Verification

R1 must run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/file_router.py \
  src/yuantus/meta_engine/web/file_conversion_router.py \
  src/yuantus/api/app.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_summary_router.py \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py

.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```

