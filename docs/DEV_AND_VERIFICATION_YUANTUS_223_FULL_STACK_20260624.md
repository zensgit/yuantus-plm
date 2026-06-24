# Yuantus 223 Full-Stack Verification - 2026-06-24

## Scope

Validate the release branch deployment on `192.168.1.223` after wiring the PLM API,
worker, DXF preview rendering, lightweight CADGF-compatible geometry artifacts, and
DedupCAD Vision integration.

This is an environment verification record. It intentionally excludes credentials.

## Services

| Service | Purpose | Endpoint / Port | Startup |
| --- | --- | --- | --- |
| `YuantusPLMApi` | PLM API | `http://192.168.1.223:7910` | Windows service, automatic |
| `YuantusPLMWorker` | Background jobs | n/a | Windows service, automatic |
| `YuantusRenderService` | DXF preview render shim | `http://127.0.0.1:8077` | Windows service, automatic |
| `YuantusCADGFShimRouter` | CAD viewer/router shim | `http://192.168.1.223:9000` | Windows service, automatic |
| `DedupCADVision` | CAD duplicate detection | `http://127.0.0.1:58001` | Windows service, automatic |

## Paths

| Path | Purpose |
| --- | --- |
| `C:\YuantusPLM` | Deployed YuantusPLM release branch archive |
| `C:\YuantusPLM\data\storage` | Local file/artifact storage |
| `C:\YuantusRenderService` | Lightweight DXF render service |
| `C:\YuantusCADGFShim` | Lightweight CADGF-compatible conversion/viewer shim |
| `C:\DedupDeploy\dedupcad-vision` | DedupCAD Vision deployment |
| `C:\YuantusDeploy\ops` | Operational check/restart/full-smoke scripts |

## Runtime Configuration

The API and worker service wrappers set the key integration URLs:

```powershell
$env:YUANTUS_DEDUP_VISION_BASE_URL='http://127.0.0.1:58001'
$env:YUANTUS_RENDER_SERVICE_BASE_URL='http://127.0.0.1:8077'
$env:YUANTUS_CADGF_ROOT='C:/YuantusCADGFShim'
$env:YUANTUS_CADGF_CONVERT_SCRIPT='C:/YuantusCADGFShim/tools/plm_convert.py'
$env:YUANTUS_CADGF_DXF_PLUGIN_PATH='C:/YuantusCADGFShim/plugins/cadgf_dxf_importer_plugin.dll'
$env:YUANTUS_CADGF_ROUTER_BASE_URL='http://127.0.0.1:9000'
$env:YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL='http://192.168.1.223:9000'
```

## Operational Scripts

Run these on `192.168.1.223`:

```powershell
C:\YuantusDeploy\ops\check_yuantus_stack.ps1
C:\YuantusDeploy\ops\restart_yuantus_stack.ps1
C:\YuantusDeploy\ops\full_smoke_yuantus_stack.ps1
```

The full smoke script creates a DXF, imports it through `/api/v1/cad/import`, waits
for `cad_preview`, `cad_geometry`, and `cad_dedup_vision`, then verifies the generated
preview, geometry, manifest, document, metadata, dedup payload, and viewer URL.

## Verification Results

Latest full smoke:

```json
{
  "jobs_completed": true,
  "endpoints_ok": true,
  "viewer_ready": true,
  "viewer_mode": "full"
}
```

Verified endpoint classes:

- `GET /api/v1/health`
- `GET /api/v1/cad/capabilities`
- `GET /api/v1/integrations/health`
- `POST /api/v1/cad/import`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/file/{file_id}/preview`
- `GET /api/v1/file/{file_id}/geometry`
- `GET /api/v1/file/{file_id}/cad_manifest?rewrite=1`
- `GET /api/v1/file/{file_id}/cad_document`
- `GET /api/v1/file/{file_id}/cad_metadata`
- `GET /api/v1/file/{file_id}/cad_dedup`
- `GET http://192.168.1.223:9000/tools/web_viewer/index.html?...`

## Limitations

- `YuantusCADGFShim` is a lightweight compatibility shim, not a full CADGameFusion
  replacement. It emits minimal line-based glTF, document JSON, manifest JSON, and
  metadata so the PLM artifact/viewer-readiness flow can be validated.
- `YuantusRenderService` is a lightweight DXF renderer. DWG still requires a proper
  DWG-to-DXF converter or a production render/CAD service.
- STEP/IGES high-fidelity conversion remains dependent on FreeCAD/CadQuery or a
  production CAD connector.

## Replacement Path

When real CADGameFusion artifacts are available, replace the shim values with the
real paths and restart `YuantusPLMApi` and `YuantusPLMWorker`:

```powershell
$env:YUANTUS_CADGF_ROOT='<CADGameFusion root>'
$env:YUANTUS_CADGF_CONVERT_SCRIPT='<CADGameFusion root>/tools/plm_convert.py'
$env:YUANTUS_CADGF_DXF_PLUGIN_PATH='<CADGameFusion build>/plugins/<cadgf dxf plugin>'
```

Then rerun:

```powershell
C:\YuantusDeploy\ops\full_smoke_yuantus_stack.ps1
```
