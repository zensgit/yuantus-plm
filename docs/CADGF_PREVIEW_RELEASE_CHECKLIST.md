# CADGF Preview Release Checklist

This checklist covers the minimal steps to enable CADGF preview behind the PLM and
validate the viewer rewrite path.

## 1) Prereqs
- CADGameFusion repo available on the host
- CADGF router service start command verified
- PLM API reachable (health check OK)

## 2) Router Service
- Start router:
  ```bash
  python3 /path/to/CADGameFusion/tools/plm_router_service.py \
    --host 127.0.0.1 --port 9000 \
    --default-plugin /path/to/CADGameFusion/build_vcpkg/plugins/libcadgf_json_importer_plugin.dylib \
    --default-convert-cli /path/to/CADGameFusion/build_vcpkg/tools/convert_cli
  ```
- Confirm health:
  ```bash
  curl -s http://127.0.0.1:9000/health
  ```

## 3) Reverse Proxy
- Expose router under `/cadgf/` on the PLM host:
  ```nginx
  location /cadgf/ {
    proxy_pass http://127.0.0.1:9000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
  ```

## 4) PLM Environment
- Required:
  ```bash
  export YUANTUS_CADGF_ROUTER_BASE_URL="http://127.0.0.1:9000"
  export YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL="https://plm.example.com/cadgf"
  export YUANTUS_CADGF_DEFAULT_EMIT="json,gltf,meta"
  export YUANTUS_CADGF_ROUTER_TIMEOUT_SECONDS="60"
  ```
- Optional:
  ```bash
  export YUANTUS_CADGF_ROUTER_AUTH_TOKEN="replace-with-bearer-token"
  export YUANTUS_CAD_PREVIEW_PUBLIC="false"
  export YUANTUS_CAD_PREVIEW_CORS_ORIGINS=""
  ```

## 5) PLM Validation (minimal)
- Upload a DXF to `/api/v1/file/upload` or `/api/v1/cad/import`.
- Fetch file metadata and confirm `cad_viewer_url` is present.
- Open `cad_viewer_url` in a browser and confirm the viewer loads.
- Validate manifest rewrite:
  ```bash
  FILE_ID="<file id>"
  curl -s "https://plm.example.com/api/v1/file/${FILE_ID}/cad_manifest?rewrite=1"
  ```

## 6) Regression Hook (optional)
- Local regression (public base):
  ```bash
  RUN_CADGF_PUBLIC_BASE=1 scripts/verify_all.sh
  ```

## 7) Rollback
- Stop CADGF router service.
- Unset `YUANTUS_CADGF_ROUTER_BASE_URL` and `YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL`.
