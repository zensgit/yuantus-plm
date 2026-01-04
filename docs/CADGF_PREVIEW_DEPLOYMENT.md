# CADGF Preview Deployment (Same-Origin)

## Goal
Serve CADGameFusion preview under the same origin as the PLM API so the viewer can load
`/api/v1/file/{id}/cad_manifest?rewrite=1` without CORS.

## Components
- CADGameFusion router service (`tools/plm_router_service.py`)
- Yuantus API (`yuantus.api.app:app`)
- Reverse proxy (Nginx)

## Reverse Proxy (Nginx)
Expose the router under `/cadgf/` on the PLM host:

```nginx
location /cadgf/ {
  proxy_pass http://127.0.0.1:9000/;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## CADGF Router Start
```bash
python3 /path/to/CADGameFusion/tools/plm_router_service.py \
  --host 127.0.0.1 --port 9000 \
  --default-plugin /path/to/CADGameFusion/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib \
  --default-convert-cli /path/to/CADGameFusion/build_vcpkg/tools/convert_cli
```

## Yuantus Configuration
```bash
export YUANTUS_CADGF_ROUTER_BASE_URL="https://plm.example.com/cadgf"
export YUANTUS_CAD_PREVIEW_PUBLIC="false"
```

## Verify (Minimal)
1) Upload a DXF to Yuantus.
2) Fetch metadata and open `cad_viewer_url`.
3) Confirm `cad_manifest?rewrite=1` returns absolute URLs:

```bash
FILE_ID="<file id>"
curl -s "https://plm.example.com/api/v1/file/${FILE_ID}" \
  | python3 - <<'PY'
import json,sys
data = json.load(sys.stdin)
print("cad_viewer_url", data.get("cad_viewer_url"))
PY

curl -s "https://plm.example.com/api/v1/file/${FILE_ID}/cad_manifest?rewrite=1" \
  | python3 - <<'PY'
import json,sys
data = json.load(sys.stdin)
print("artifacts", data.get("artifacts", {}))
PY
```

## Notes
- The `/api/v1/cad-preview` page is for manual debugging; it uses the router's
  `viewer_url`, which may point to the router host:port. Use it only if the
  router base URL is directly reachable.
- If you later enable router auth, set `YUANTUS_CADGF_ROUTER_AUTH_TOKEN` and pass
  `--auth-token` when starting the router.

## Rollback
- Unset `YUANTUS_CADGF_ROUTER_BASE_URL` or stop the router service to disable preview.
