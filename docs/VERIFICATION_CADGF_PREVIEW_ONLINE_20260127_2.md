# CADGF Preview Online Verification Report

## Inputs
- BASE_URL: http://127.0.0.1:7910
- TENANT/ORG: tenant-1 / org-1
- SAMPLE_FILE: /Users/huazhou/Downloads/训练图纸/训练图纸/J2824002-06上封头组件v2.dwg

## Results
- login_ok: yes
- upload_ok: yes
- conversion_ok: yes
- viewer_load: yes
- manifest_rewrite: yes
- metadata_present: n/a
- jobs_count: 1
- file_id: 630a312a-628f-40b7-b5cc-5f317536aa5e
- cad_viewer_url: http://localhost:9000/tools/web_viewer/index.html?manifest=http%3A%2F%2F127.0.0.1%3A7910%2Fapi%2Fv1%2Ffile%2F630a312a-628f-40b7-b5cc-5f317536aa5e%2Fcad_manifest%3Frewrite%3D1
- exit_code: 0

## Jobs (import response)
```json
[
  {
    "id": "d079ff0d-37ce-426e-b54c-c8a409c8421b",
    "status": "pending",
    "task_type": "cad_geometry"
  }
]
```

## Manifest Artifacts (rewrite=1)
```json
{
  "document_json": "http://127.0.0.1:7910/api/v1/file/630a312a-628f-40b7-b5cc-5f317536aa5e/cad_document",
  "mesh_bin": "mesh.bin",
  "mesh_gltf": "http://127.0.0.1:7910/api/v1/file/630a312a-628f-40b7-b5cc-5f317536aa5e/cad_asset/mesh.gltf",
  "mesh_metadata": "http://127.0.0.1:7910/api/v1/file/630a312a-628f-40b7-b5cc-5f317536aa5e/cad_metadata"
}
```
