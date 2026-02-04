# Product Detail Field Mapping (YuantusPLM)

This document defines the stable field contract for `GET /api/v1/products/{item_id}` so UI
and federation adapters can map values consistently.

## Endpoint

```
GET /api/v1/products/{item_id}
```

### Query Params

- `include_versions` (default: true)
- `include_files` (default: true)
- `include_version_files` (default: false)
- `include_bom_summary` (default: false)
- `bom_summary_depth` (default: 1)
- `bom_effective_at` (ISO datetime, optional)
- `include_bom_obsolete_summary` (default: false)
- `bom_obsolete_recursive` (default: true)
- `bom_obsolete_levels` (default: 10, -1 for unlimited)
- `include_bom_weight_rollup` (default: false)
- `bom_weight_levels` (default: 3)
- `bom_weight_effective_at` (ISO datetime, optional)
- `bom_weight_rounding` (default: 3, set to null to skip rounding)
- `include_where_used_summary` (default: false)
- `where_used_recursive` (default: false)
- `where_used_max_levels` (default: 5)
- `include_document_summary` (default: false)
- `include_eco_summary` (default: false)

## Response Top-Level

```json
{
  "item": { ... },
  "current_version": { ... },
  "versions": [ ... ],
  "files": [ ... ],
  "version_files": [ ... ],
  "bom_summary": { ... },
  "bom_obsolete_summary": { ... },
  "bom_weight_rollup_summary": { ... },
  "where_used_summary": { ... },
  "document_summary": { ... },
  "eco_summary": { ... }
}
```

Sections are included based on `include_*` flags.

## Item Field Mapping

`item` contains canonical fields plus UI-friendly aliases.

| Field | Source | Notes |
|------|--------|-------|
| `id` | Item.id | UUID |
| `type` | Item.item_type_id | Canonical type |
| `item_type_id` | Item.item_type_id | Alias for UI/federation |
| `item_type` | Item.item_type_id | Alias for UI/federation |
| `item_number` | properties.item_number \/ properties.number | Canonical part number |
| `number` | properties.item_number \/ properties.number | Alias |
| `name` | properties.name | Canonical name |
| `item_name` | properties.name | Alias |
| `title` | properties.name | Alias |
| `revision` | properties.revision | Optional |
| `state` | Item.state | Canonical state |
| `status` | Item.state | Alias |
| `current_state` | Item.state | Alias |
| `config_id` | Item.config_id | Optional |
| `generation` | Item.generation | Optional |
| `is_current` | Item.is_current | Optional |
| `current_version_id` | Item.current_version_id | Optional |
| `description` | properties.description | Optional |
| `properties` | Item.properties | Full properties JSON |
| `created_at` | Item.created_at | ISO string |
| `updated_at` | Item.updated_at | ISO string |
| `created_on` | Item.created_at | Alias |
| `modified_on` | Item.updated_at | Alias |
| `created_by_id` | Item.created_by_id | Optional |
| `modified_by_id` | Item.modified_by_id | Optional |
| `owner_id` | Item.owner_id | Optional |

### Alias Rationale

UI adapters (e.g., MetaSheet federation) may reference `item_type`, `status`, `created_on`
from legacy PLM systems. The aliases above ensure stable mapping without extra transforms.

## Version Fields

`current_version` and `versions[]` share the same schema:

- `id`, `item_id`, `generation`, `revision`, `version_label`
- `state`, `is_current`, `is_released`
- `branch_name`, `checked_out_by_id`, `checked_out_at`
- `released_at`, `created_at`

## File Entry Fields (`files[]`)

`files[]` includes CAD summary fields and URLs for previews/conversions.

| Field | Notes |
|------|-------|
| `attachment_id` | ItemFile.id |
| `file_id` | FileContainer.id |
| `filename` | Original filename |
| `name` | Alias for filename |
| `file_role` | ItemFile.file_role |
| `role` | Alias for file_role |
| `description` | ItemFile.description |
| `file_type` | Extension |
| `type` | Alias for file_type |
| `mime_type` | MIME |
| `mime` | Alias for mime_type |
| `file_size` | Bytes |
| `size` | Alias for file_size |
| `document_type` | 2d/3d/pr/other |
| `version` | Alias for document_version |
| `is_cad` | Derived by extension |
| `is_native_cad` | Bool |
| `cad_format` | CAD format tag |
| `cad_connector_id` | Connector id (if any) |
| `cad_document_schema_version` | CADGF schema version |
| `cad_review_state` | pending/approved/rejected |
| `cad_review_note` | Optional |
| `cad_review_by_id` | Reviewer id |
| `cad_reviewed_at` | ISO datetime |
| `conversion_status` | pending/processing/completed/failed |
| `author` | Optional |
| `source_system` | Optional |
| `source_version` | Optional |
| `document_version` | Optional |
| `preview_url` | `/api/v1/file/{id}/preview` if available |
| `geometry_url` | `/api/v1/file/{id}/geometry` if available |
| `cad_manifest_url` | `/api/v1/file/{id}/cad_manifest` if available |
| `cad_document_url` | `/api/v1/file/{id}/cad_document` if available |
| `cad_metadata_url` | `/api/v1/file/{id}/cad_metadata` if available |
| `cad_bom_url` | `/api/v1/file/{id}/cad_bom` if available |
| `download_url` | `/api/v1/file/{id}/download` |
| `created_at` | ISO datetime |
| `updated_at` | ISO datetime |
| `created_on` | Alias for created_at |
| `updated_on` | Alias for updated_at |

## Summary Sections

### `bom_summary`

```json
{
  "authorized": true,
  "depth": 1,
  "direct_children": 1,
  "total_children": 3,
  "max_depth": 2
}
```

### `where_used_summary`

```json
{
  "authorized": true,
  "count": 2,
  "recursive": true,
  "max_levels": 5,
  "sample": [
    {"id":"...","item_number":"...","name":"...","level":1}
  ]
}
```

### `bom_obsolete_summary`

```json
{
  "authorized": true,
  "count": 2,
  "recursive": true,
  "max_levels": 10,
  "sample": [
    {
      "relationship_id": "...",
      "parent_id": "...",
      "child_id": "...",
      "replacement_id": "...",
      "reasons": ["obsolete", "revision_conflict"]
    }
  ]
}
```

### `bom_weight_rollup_summary`

```json
{
  "authorized": true,
  "levels": 3,
  "effective_at": "",
  "total_weight": 12.5,
  "unit": "kg",
  "root": {
    "id": "...",
    "name": "...",
    "weight": 12.5,
    "children": []
  }
}
```

### `document_summary`

```json
{
  "authorized": true,
  "count": 2,
  "state_counts": {"Released": 1, "Draft": 1},
  "sample": [
    {"id":"...","item_number":"...","name":"...","state":"...","current_version_id":"..."}
  ],
  "items": [
    {"id":"...","item_number":"...","name":"...","state":"...","current_version_id":"..."}
  ]
}
```

### `eco_summary`

```json
{
  "authorized": true,
  "count": 1,
  "state_counts": {"done": 1},
  "pending_approvals": {"count": 0, "items": []},
  "last_applied": {"eco_id":"...","name":"...","product_version_after":"...","updated_at":"..."},
  "items": [
    {"eco_id":"...","name":"...","state":"...","stage_id":"...","stage_name":"...","approval_deadline":"..."}
  ]
}
```

## Verification

```bash
bash scripts/verify_product_detail.sh http://127.0.0.1:7910 tenant-1 org-1
```

Also see:
- `docs/VERIFICATION_PRODUCT_DETAIL_ALIASES_20260129_0918.md`
- `docs/VERIFICATION_PRODUCT_DETAIL_CAD_SUMMARY_20260129_0936.md`
