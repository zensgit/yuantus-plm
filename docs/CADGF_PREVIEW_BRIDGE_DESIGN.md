# CADGF Preview Bridge - Design

## Goal
Provide a minimal PLM-side page that uploads a CAD file to the CADGameFusion router service and opens the returned web preview, without exposing router auth tokens to the browser.

## Scope
- Static HTML page served by the Yuantus API.
- Uses the CADGameFusion router service `/convert` + `/status` endpoints.
- Supports optional migration/validation flags for document schema control.

## Routes
- `GET /api/v1/cad-preview`
- `POST /api/v1/cad-preview/convert` (proxy to CADGF router `/convert`)
- `GET /api/v1/cad-preview/status/{task_id}` (proxy to CADGF router `/status`)
- `GET /api/v1/file/{file_id}/cad_manifest?rewrite=1` (viewer-ready manifest)
- `GET /api/v1/file/{file_id}/cad_asset/{asset_name}` (viewer assets)

## Files
- `src/yuantus/web/cad_preview.html` (static UI)
- `src/yuantus/api/routers/cad_preview.py` (router endpoint)
- `src/yuantus/api/app.py` (router registration)

## Configuration
- `YUANTUS_CADGF_ROUTER_BASE_URL`
- `YUANTUS_CADGF_ROUTER_AUTH_TOKEN`
- `YUANTUS_CADGF_DEFAULT_EMIT`
- `YUANTUS_CADGF_ROUTER_TIMEOUT_SECONDS`
- `YUANTUS_CAD_PREVIEW_PUBLIC` (optional, expose CAD preview assets without auth)
- `YUANTUS_CAD_PREVIEW_CORS_ORIGINS` (optional, comma-separated origins for CAD preview)

## UI Inputs
- Router base URL (server config only)
- File upload
- Emit mode (`json`, `gltf`, `meta`)
- Project ID / Document label
- Plugin + convert_cli override (optional)
- Migration/validation toggles + schema target

## Notes
- Router must be started separately (CADGameFusion `tools/plm_router_service.py`).
- The UI calls Yuantus proxy endpoints; the router auth token stays server-side.
- The CAD viewer URL uses `cad_manifest?rewrite=1` so artifacts resolve to API URLs.
- If the viewer URL is hosted on a different domain, enable CORS/public access for CAD preview assets.

## Deployment Guidance
- Recommended: host the CADGF viewer under the same origin as the PLM (reverse proxy or static hosting) to avoid CORS and keep auth enabled.
- Cross-origin: set `YUANTUS_CAD_PREVIEW_PUBLIC=true` and `YUANTUS_CAD_PREVIEW_CORS_ORIGINS=<viewer origin>` so the viewer can read manifest/assets.

## Same-Origin Reverse Proxy (Nginx)
Example: serve the CADGF router under `/cadgf/` on the same host as the PLM API.

```nginx
location /cadgf/ {
  proxy_pass http://127.0.0.1:9000/;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

PLM configuration:
- `YUANTUS_CADGF_ROUTER_BASE_URL=https://plm.example.com/cadgf`
- keep `YUANTUS_CAD_PREVIEW_PUBLIC=false` (default)

## Same-Origin Reverse Proxy (Caddy)
```caddy
handle_path /cadgf/* {
  reverse_proxy 127.0.0.1:9000
}
```

PLM configuration:
- `YUANTUS_CADGF_ROUTER_BASE_URL=https://plm.example.com/cadgf`
