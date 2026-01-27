# CAD Connector Plugin Spec (DocDoku-style, Yuantus Adaptation)

## Goal
Define a DocDoku-inspired **conversion microservice** contract for real CAD connectors, while remaining independent from PLM runtime/stack. The PLM triggers conversions and the plugin returns standardized artifacts (geometry + metadata) for storage and UI.

## Design Principles (Borrowed from DocDoku)
- **Conversion service is isolated** from PLM core.
- **Converter selection by format** (ext-based routing).
- **Return normalized artifacts** (geometry + bbox + metadata).
- **Loose coupling** via HTTP + JSON schemas.

## Architecture
```
PLM API -> enqueue job -> Connector Service
                         (plugin / converter)
           <- result/callback or polling
```

Two supported patterns:
1) **Synchronous (small files)**: PLM calls `/convert` and receives results.
2) **Asynchronous (large files)**: PLM calls `/convert`, connector responds with `job_id`, PLM polls `/jobs/{id}` or connector calls PLM callback.

## Endpoints
### 1) Health
`GET /health`
```json
{"ok": true, "service": "cad-connector", "version": "1.0.0"}
```

### 2) Capabilities
`GET /capabilities`
```json
{
  "formats": ["dwg", "dxf", "step", "stp", "prt", "sldprt", "catpart"],
  "features": {
    "extract": true,
    "geometry": true,
    "bom": true,
    "preview": true,
    "lod": false
  },
  "limits": {"max_bytes": 10737418240}
}
```

### 3) Convert / Extract / Geometry
`POST /convert`
- Accepts a **file** or a **file_url** (PLM signed URL).
- Returns standardized artifacts.

Request (file upload):
```json
{
  "file_name": "part_001.step",
  "file_url": "https://.../signed-url",
  "format": "step",
  "tenant_id": "tenant-1",
  "org_id": "org-1",
  "mode": "extract|geometry|preview|bom|all",
  "callback_url": "https://plm/api/v1/cad/callback",
  "metadata": {
    "item_id": "...",
    "file_id": "..."
  }
}
```

Response (sync):
```json
{
  "ok": true,
  "job_id": "optional",
  "artifacts": {
    "geometry": {
      "gltf_url": "https://.../mesh.gltf",
      "bin_url": "https://.../mesh.bin",
      "bbox": [0,0,0, 10,20,30]
    },
    "preview": {
      "png_url": "https://.../preview.png"
    },
    "attributes": {
      "part_number": "P-001",
      "revision": "A",
      "description": "...",
      "material": "AL6061"
    },
    "bom": {
      "nodes": [],
      "edges": []
    }
  }
}
```

### 4) Job status (async)
`GET /jobs/{job_id}`
```json
{"ok": true, "status": "pending|running|completed|failed", "artifacts": {...}}
```

## Error Handling
- HTTP 4xx for request/validation errors
- HTTP 5xx for conversion failures
- Response:
```json
{"ok": false, "error": "message", "details": {"code": "CONVERSION_FAILED"}}
```

## Security
- Auth header (optional): `Authorization: Bearer <token>`
- Connector should support **token passthrough** for PLM callback.
- Prefer **signed URLs** (short TTL) over raw file payload for large files.

## Mapping to Yuantus
| Yuantus Stage | Connector Call | Result Used By |
|--------------|----------------|----------------|
| cad_extract  | /convert (extract) | attributes endpoint |
| cad_geometry | /convert (geometry) | cad_viewer_url / manifest |
| cad_preview  | /convert (preview) | file preview | 
| bom import   | /convert (bom) | BOM tree | 

## Implementation Path
1) **Stub Connector** (for integration testing)
   - returns fake attributes + dummy glTF
2) **FreeCAD/Assimp Connector** (open-source core)
   - covers step/stl/iges
3) **Commercial Connectors** (NX/Creo/SW/CATIA)
   - run on Windows with license

## Notes from DocDoku (reference)
DocDoku uses a dedicated conversion microservice, selecting a converter by file extension and returning OBJ + bbox + LOD metadata for visualization. We reuse this **pattern** but standardize on glTF/GLB for Yuantus UI.

