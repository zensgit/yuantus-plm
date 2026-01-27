# CADGF Preview Online (Design)

## Goal
Enable online CAD preview by routing converted geometry (CADGF) into the PLM file pipeline and serving a web viewer URL that references a rewritten manifest on the PLM API.

## Components
- Yuantus PLM API
  - `/api/v1/cad/import` uploads CAD file and creates a `cad_geometry` job.
  - `/api/v1/file/{id}` exposes `cad_viewer_url` after geometry generation.
  - `/api/v1/file/{id}/cad_manifest?rewrite=1` rewrites manifest URLs back to PLM.
- CADGF router
  - `tools/plm_router_service.py` from CADGameFusion.
  - Uses `convert_cli` and `libcadgf_json_importer_plugin` to generate geometry.
- CADGF web viewer
  - `tools/web_viewer/index.html` loads manifest via PLM API.

## Data Flow
1. Client uploads CAD to PLM (`/api/v1/cad/import`).
2. Worker or router generates geometry (cad_geometry job).
3. PLM sets `cad_viewer_url` pointing to CADGF web viewer.
4. Viewer requests manifest from PLM (rewrite=1), then fetches mesh/metadata.

```
Client -> PLM /cad/import -> Storage
                 |
                 v
           cad_geometry job
                 |
                 v
          CADGF router
                 |
                 v
         PLM cad_manifest (rewrite=1)
                 |
                 v
        CADGF web viewer loads
```

## Runtime Configuration
- CADGF router
  - `CADGF_ROOT=/path/to/CADGameFusion` (must include `tools/plm_router_service.py`)
  - `CADGF_PLUGIN_PATH=/path/to/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib`
  - `CADGF_CONVERT_CLI=/path/to/build_vcpkg/tools/convert_cli`
  - `CADGF_ROUTER_HOST` / `CADGF_ROUTER_PORT` (default 127.0.0.1:9000)
- PLM integration
  - `YUANTUS_CADGF_ROUTER_BASE_URL=http://127.0.0.1:9000`

## Local Startup
```
CADGF_ROOT=/Users/huazhou/Downloads/Github/CADGameFusion-legacy \
  scripts/run_cadgf_router.sh
```

## Notes
- The current CADGF router was launched from `CADGameFusion-legacy` because the
  `CADGameFusion-codex-yuantus` worktree is a clean checkout without build artifacts.
- When needed, build outputs can be generated inside `CADGameFusion-codex-yuantus`
  to make it self-contained.

## Verification
See `docs/VERIFICATION_CADGF_PREVIEW_ONLINE_20260127.md`.
