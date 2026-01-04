# CADGF Preview Environment Reference

This file summarizes the Yuantus environment variables used by the CADGF
preview bridge. Use it as a copy/paste checklist when deploying.

## Minimal (local dev)
```bash
export YUANTUS_CADGF_ROUTER_BASE_URL="http://127.0.0.1:9000"
export YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL=""
export YUANTUS_CADGF_DEFAULT_EMIT="json,gltf,meta"
export YUANTUS_CADGF_ROUTER_TIMEOUT_SECONDS="60"
export YUANTUS_CAD_PREVIEW_PUBLIC="false"
export YUANTUS_CAD_PREVIEW_CORS_ORIGINS=""
```

## Reverse Proxy (router local, viewer public)
```bash
export YUANTUS_CADGF_ROUTER_BASE_URL="http://127.0.0.1:9000"
export YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL="https://plm.example.com/cadgf"
export YUANTUS_CAD_PREVIEW_PUBLIC="false"
```

## Router Auth (optional)
```bash
export YUANTUS_CADGF_ROUTER_AUTH_TOKEN="replace-with-bearer-token"
```

## Cross-Origin Viewer (optional)
If the viewer runs on a different origin, you can temporarily open CAD preview
assets to unauthenticated access.
```bash
export YUANTUS_CAD_PREVIEW_PUBLIC="true"
export YUANTUS_CAD_PREVIEW_CORS_ORIGINS="https://viewer.example.com"
```

## CADGF Conversion Paths (2D pipeline)
```bash
export YUANTUS_CADGF_ROOT="/path/to/CADGameFusion"
export YUANTUS_CADGF_CONVERT_SCRIPT="/path/to/CADGameFusion/tools/plm_convert.py"
export YUANTUS_CADGF_CONVERT_CLI="/path/to/CADGameFusion/build_vcpkg/tools/convert_cli"
export YUANTUS_CADGF_DXF_PLUGIN_PATH="/path/to/CADGameFusion/build_vcpkg/plugins/libcadgf_dxf_importer_plugin.dylib"
export YUANTUS_CADGF_PYTHON_BIN="/opt/homebrew/bin/python3.12"
```

Notes:
- `YUANTUS_CADGF_ROUTER_PUBLIC_BASE_URL` is only for browser-facing viewer URLs.
  The server still calls `YUANTUS_CADGF_ROUTER_BASE_URL` for router requests.
- For DWG input, convert to DXF before calling the CADGF 2D pipeline.
