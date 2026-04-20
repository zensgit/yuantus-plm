# DEV_AND_VERIFICATION_CAD_BACKEND_PROFILE_SCOPE_OVERRIDES_20260420

## Goal

Make the CAD backend profile tenant/org aware without introducing a new table or changing the already-shipped profile vocabulary.

## Summary

This round moves CAD backend profile selection from env-only resolution to scoped policy resolution:

1. org override
2. tenant default override
3. environment profile fallback

The profile names remain unchanged:

- `local-baseline`
- `hybrid-auto`
- `external-enterprise`

## Code Changes

### 1. Added a scoped CAD backend profile service

- Files:
  - `src/yuantus/meta_engine/services/cad_backend_profile_service.py`
  - `src/yuantus/meta_engine/services/plugin_config_service.py`

What it does:

- Reuses the existing `meta_plugin_configs` table.
- Stores CAD backend policy under plugin id `cad-backend-profile`.
- Reads config key `backend_profile`.
- Resolves profile with fallback chain:
  - `tenant + org`
  - `tenant + default`
  - environment setting

Why this shape:

- No migration required.
- No new generic config abstraction required.
- The task layer can stay thin and only ask for the already-resolved profile.

### 2. Wired scoped resolution into CAD jobs

- File:
  - `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`

Changes:

- `cad_preview`
- `cad_geometry`
- `cad_bom`

Behavior:

- The worker now resolves the backend profile using the current request/job tenant/org context.
- `external-enterprise` remains fail-fast.
- `local-baseline` disables connector-backed 3D preview/geometry for that scope.
- `cad_bom` remains connector-backed only, so a local-only scope will report connector unavailable for BOM import.

### 3. Added scoped management/read endpoints

- File:
  - `src/yuantus/meta_engine/web/cad_router.py`

New endpoints:

- `GET /api/v1/cad/backend-profile`
- `PUT /api/v1/cad/backend-profile`
- `DELETE /api/v1/cad/backend-profile?scope=org|tenant`

Rules:

- `GET` requires authenticated user.
- `PUT`/`DELETE` require admin or superuser role.
- `PUT` accepts:
  - `profile`
  - `scope=org|tenant`
- `DELETE` removes the override for the selected scope and returns the newly effective profile.

### 4. Made capabilities scope-aware

- File:
  - `src/yuantus/meta_engine/web/cad_router.py`

`GET /api/v1/cad/capabilities` now uses the scoped profile resolver when tenant/org context is present.

Result:

- `integrations.cad_connector.profile` can now show:
  - env resolution
  - tenant default override
  - tenant/org override
- feature availability and connector enabled/disabled state now follow the scoped effective profile.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_cad_backend_profile.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_service.py \
  src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py \
  src/yuantus/meta_engine/tests/test_cad_capabilities_router.py
```

Result:

- `18 passed`

Coverage:

- env fallback remains intact
- org override beats env
- tenant default fallback works
- invalid scoped config is ignored
- backend-profile router read/update/delete contracts
- capabilities endpoint honors scoped local override

Doc/index verification:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py
```

## Files Changed

- `src/yuantus/meta_engine/services/plugin_config_service.py`
- `src/yuantus/meta_engine/services/cad_backend_profile_service.py`
- `src/yuantus/meta_engine/tasks/cad_pipeline_tasks.py`
- `src/yuantus/meta_engine/web/cad_router.py`
- `src/yuantus/meta_engine/tests/test_cad_backend_profile.py`
- `src/yuantus/meta_engine/tests/test_cad_backend_profile_service.py`
- `src/yuantus/meta_engine/tests/test_cad_backend_profile_router.py`
- `src/yuantus/meta_engine/tests/test_cad_capabilities_router.py`
- `docs/CAD_CONNECTORS.md`

## Operational Note

Claude Code CLI is available on this machine and supports non-interactive `-p/--print` mode. It can be used as a sidecar reviewer or prompt-driven scaffold tool, but this implementation was kept on the main line to avoid uncontrolled edits to the active worktree.
