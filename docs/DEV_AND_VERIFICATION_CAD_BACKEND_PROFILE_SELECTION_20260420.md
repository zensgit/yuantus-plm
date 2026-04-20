# DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SELECTION_20260420

## Goal

Turn the existing mixed CAD conversion behavior into an explicit customer-selectable backend strategy without breaking current jobs.

## What Changed

### 1. Added a formal backend-profile setting

- File:
  - `src/yuantus/config/settings.py`
  - `src/yuantus/config/cad_backend_profile.py`
- New env:
  - `YUANTUS_CAD_CONVERSION_BACKEND_PROFILE`
- Supported values:
  - `auto`
  - `local-baseline`
  - `hybrid-auto`
  - `external-enterprise`

Resolution rules:

1. If `YUANTUS_CAD_CONVERSION_BACKEND_PROFILE` is explicitly set to `local-baseline`, `hybrid-auto`, or `external-enterprise`, that profile wins.
2. If the value is `auto`, Yuantus preserves the legacy behavior:
   - no connector URL -> `local-baseline`
   - connector URL + `CAD_CONNECTOR_MODE=optional` -> `hybrid-auto`
   - connector URL + `CAD_CONNECTOR_MODE=required` -> `external-enterprise`

### 2. Wired the profile into CAD preview and geometry jobs

- File:
  - `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`

Behavior after this change:

- `local-baseline`
  - Never uses the external CAD connector for connector-backed 3D preview/geometry.
- `hybrid-auto`
  - Uses the external connector when available and falls back to local conversion on failure.
- `external-enterprise`
  - Fails fast if the connector is not configured.
  - Fails the job if connector conversion fails.

Unchanged scope:

- `stl/obj/gltf/glb` still short-circuit as already-viewable formats.
- `dwg/dxf` still route through the CADGF path.
- `cad_bom` remains connector-backed only.

### 3. Exposed the selected profile in capabilities

- File:
  - `src/yuantus/meta_engine/web/cad_router.py`

`GET /api/v1/cad/capabilities` now returns:

```json
{
  "integrations": {
    "cad_connector": {
      "configured": true,
      "enabled": true,
      "mode": "disabled",
      "profile": {
        "configured": "hybrid-auto",
        "effective": "hybrid-auto",
        "source": "profile",
        "options": [
          "local-baseline",
          "hybrid-auto",
          "external-enterprise"
        ]
      }
    }
  }
}
```

This keeps the existing contract shape and adds the profile metadata only under `integrations.cad_connector`.

### 4. Fixed an existing OpenAPI mismatch

- File:
  - `src/yuantus/meta_engine/web/file_router.py`

`GET /api/v1/file/supported-formats` is now explicitly marked `deprecated=True`, matching the existing OpenAPI contract test.

## Why This Matters

- It lets Yuantus support the two customer paths discussed during review:
  - built-in local conversion stack
  - external enterprise converter stack
- It keeps one stable product contract for downstream preview/geometry consumers.
- It reduces ambiguity around FreeCAD usage:
  - FreeCAD remains part of the local baseline and hybrid fallback path for STEP/IGES preview/geometry.
  - Customers who want stricter external conversion can select `external-enterprise`.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py
```

Result:

- `11 passed`

Coverage added:

- backend-profile resolution
- explicit profile override over legacy connector mode
- task-layer fail-fast for `external-enterprise`
- capability-surface exposure of configured/effective profile
- supported-formats OpenAPI deprecation contract

## Files Changed

- `src/yuantus/config/__init__.py`
- `src/yuantus/config/settings.py`
- `src/yuantus/config/cad_backend_profile.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/web/file_router.py`
- `src/yuantus/meta_engine/tests/test_cad_backend_profile.py`
- `src/yuantus/meta_engine/tests/test_cad_capabilities_router.py`
- `docs/CAD_CONNECTORS.md`

## Recommended Next Step

If customer configuration needs to become tenant-aware later, keep this profile vocabulary unchanged and only move the source of truth from env settings to tenant/org policy. The task/router wiring added here can stay as-is.
