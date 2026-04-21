# CAD STEP/IGES Backend Choice - Development And Verification

Date: 2026-04-21

## 1. Goal

Add a bounded runtime choice for STEP/IGES preview and geometry conversion while preserving the existing CAD backend profile contract.

The new switch is environment-level only:

```bash
CAD_STEP_IGES_BACKEND=auto|local|connector
```

It applies only to STEP/IGES 3D preview and geometry paths under `hybrid-auto`. Existing profile semantics remain strict:

- `local-baseline` always uses the local backend for STEP/IGES.
- `external-enterprise` always requires the connector backend.
- `hybrid-auto` may use `auto`, `local`, or `connector`.

## 2. Code Changes

- Added `CAD_STEP_IGES_BACKEND` to settings with default `auto`.
- Added normalization and effective-resolution helpers in `yuantus.config.cad_backend_profile`.
- Routed STEP/IGES preview and geometry in `cad_pipeline_tasks.py` through the new per-file backend choice.
- Preserved DWG/DXF CADGF handling and glTF/STL/OBJ short-circuit behavior.
- Added read-only reporting to `GET /cad/capabilities` under `integrations.cad_connector.step_iges_backend`.

## 3. Non-Goals

- No new CAD backend profile names.
- No `/cad/backend-profile` request or response shape change.
- No tenant/org scoped subconfiguration for STEP/IGES.
- No removal of FreeCAD/local conversion.
- No shared-dev write/bootstrap operation.
- No scheduler, retry, or batch-resilience changes.

## 4. Contract

`GET /cad/capabilities` now reports:

```json
{
  "integrations": {
    "cad_connector": {
      "step_iges_backend": {
        "configured": "auto",
        "effective": "connector",
        "options": ["auto", "local", "connector"],
        "formats": ["STEP", "IGES"],
        "extensions": ["step", "stp", "iges", "igs"]
      }
    }
  }
}
```

This is intentionally read-only. Operators still choose scoped CAD profile through the existing profile API, and choose STEP/IGES backend through environment configuration.

## 5. Verification

Focused CAD profile, capabilities, and doc-index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_service.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result:

```text
37 passed
```

Coverage included:

- `auto` STEP/IGES backend resolves to connector under hybrid profile with connector base URL.
- explicit `local` disables connector usage for STEP files under hybrid profile.
- explicit `connector` enables connector usage for STEP files under hybrid profile.
- non-STEP/IGES files are unaffected by the STEP/IGES switch.
- `local-baseline` remains local even when the STEP/IGES switch says connector.
- `external-enterprise` remains connector-required even when the STEP/IGES switch says local.
- capabilities response exposes configured/effective/options without changing backend-profile management API shape.

CAD queue and pipeline compatibility:

```bash
YUANTUS_AUTH_MODE=optional .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_upload_preview_queue.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_job_queue.py \
  src/yuantus/meta_engine/tests/test_cad_pipeline_version_binding.py \
  src/yuantus/meta_engine/tests/test_cad_converter_service_freecad_safety.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py
```

Result:

```text
51 passed
```

`YUANTUS_AUTH_MODE=optional` is required for this local run because the repository `.env` sets auth to required, while these legacy file-router contract tests exercise optional-auth endpoints without bearer tokens.

Whitespace check:

```bash
git diff --check
```

Result: passed with no output.

## 6. Remaining Verification

Shared-dev 142 smoke is intentionally not part of this local implementation record because the feature is not deployed there yet. After deployment, use the existing CAD profile smoke flow and verify `/cad/capabilities` reports the selected STEP/IGES backend.
