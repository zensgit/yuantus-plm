# CADGF Preview Online Verification Report

## Inputs
- BASE_URL: http://127.0.0.1:7910
- TENANT/ORG: tenant-1 / org-1
- SAMPLE_FILE: docs/samples/cadgf_preview_square.dxf

## Results
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- metadata_present: n/a
- jobs_count: 1
- file_id: 655e481c-ae40-4dec-897c-3d37e97dd64f
- cad_viewer_url: http://localhost:9000/tools/web_viewer/index.html?manifest=http%3A%2F%2F127.0.0.1%3A7910%2Fapi%2Fv1%2Ffile%2F655e481c-ae40-4dec-897c-3d37e97dd64f%2Fcad_manifest%3Frewrite%3D1
- exit_code: 0

## Jobs (import response)
```json
[
  {
    "id": "0bcd4ec8-1e3d-459c-b3cb-9d805e3de1da",
    "status": "pending",
    "task_type": "cad_geometry"
  }
]
```

## Manifest Artifacts (rewrite=1)
```json
{
  "document_json": "http://127.0.0.1:7910/api/v1/file/655e481c-ae40-4dec-897c-3d37e97dd64f/cad_document",
  "mesh_bin": "mesh.bin",
  "mesh_gltf": "http://127.0.0.1:7910/api/v1/file/655e481c-ae40-4dec-897c-3d37e97dd64f/cad_asset/mesh.gltf",
  "mesh_metadata": "http://127.0.0.1:7910/api/v1/file/655e481c-ae40-4dec-897c-3d37e97dd64f/cad_metadata"
}
```
