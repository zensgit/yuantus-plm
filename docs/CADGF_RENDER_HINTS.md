# CADGF Render Hints

Date: 2026-01-09

This note captures small, engine-friendly helpers exposed by the PLM backend
for CADGF-based previews.

## Mesh Stats
- Endpoint: `GET /api/v1/cad/files/{file_id}/mesh-stats`
- Purpose: return lightweight statistics derived from `mesh_metadata.json`.
- Typical use: pick LOD/quality settings or warn on heavy meshes.

Example response:
```json
{
  "file_id": "...",
  "stats": {
    "raw_keys": ["entities", "bounds", "triangle_count"],
    "entity_count": 120,
    "triangle_count": 24000,
    "bounds": {
      "min": [-1.0, -1.0],
      "max": [1.0, 1.0]
    }
  }
}
```

## View Overrides
- Endpoint: `PATCH /api/v1/cad/files/{file_id}/view-state`
- Payload supports `hidden_entity_ids` + `notes` to apply lightweight edits.
- Intended for client-side rendering layers that overlay CADGF geometry.
