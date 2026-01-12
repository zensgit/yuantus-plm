# BOM Compare + Pack-and-Go Plugins

This document describes the two new plugins:
- BOM Compare/Apply (`yuantus-bom-compare`)
- Pack-and-Go (`yuantus-pack-and-go`)

## Installation

Plugins are discovered from `YUANTUS_PLUGIN_DIRS` (defaults to `./plugins`).
Enable only specific plugins with:

```bash
export YUANTUS_PLUGINS_ENABLED=yuantus-bom-compare,yuantus-pack-and-go
```

The API process auto-loads plugins when `YUANTUS_PLUGINS_AUTOLOAD=true` (default).

## BOM Compare Plugin

Base path: `/api/v1/plugins/bom-compare`

### Compare BOMs

`POST /compare`

Request:
```json
{
  "item_id_a": "UUID-A",
  "item_id_b": "UUID-B",
  "compare_mode": "only_product|summarized|num_qty|by_position|by_reference",
  "relationship_types": ["Part BOM"],
  "quantity_key": "quantity",
  "position_key": "find_num",
  "refdes_key": "refdes",
  "levels": -1,
  "include_unchanged": false,
  "quantity_tolerance": 0.0,
  "filters": {
    "include_statuses": ["added", "removed"],
    "exclude_statuses": ["unchanged"],
    "child_id_regex": "^(P|A)-",
    "name_regex": "Bracket",
    "relationship_id_regex": "REL-",
    "min_delta": 0.5,
    "max_delta": 10
  }
}
```

Response:
```json
{
  "summary": {"added": 1, "removed": 0, "modified": 2, "unchanged": 10},
  "summary_filtered": {"added": 1, "removed": 0, "modified": 1, "unchanged": 0},
  "differences": [
    {
      "key": "child-id:10",
      "child_id": "UUID-CHILD",
      "name": "Part A",
      "status": "modified",
      "qty_a": 1.0,
      "qty_b": 2.0,
      "delta": 1.0,
      "position_a": "10",
      "position_b": "10",
      "refdes_a": null,
      "refdes_b": null,
      "relationship_ids_a": ["REL-A"],
      "relationship_ids_b": ["REL-B"]
    }
  ]
}
```

### Apply Changes

`POST /apply`

Request:
```json
{
  "relationship_types": ["Part BOM"],
  "changes": [
    {"op": "add", "parent_id": "UUID-A", "child_id": "UUID-NEW", "quantity": 2},
    {"op": "remove", "relationship_id": "UUID-REL"},
    {"op": "update", "relationship_id": "UUID-REL2", "quantity": 5}
  ],
  "dry_run": false,
  "preview": false
}
```

Notes:
- `add` validates cycle detection and uses AML relationship add.
- `update/remove` require relationship item ids.
- Permissions are enforced by AML.
- `preview=true` returns a planned change list without applying AML or committing.

### Export CSV

`POST /export`

Request:
```json
{
  "item_id_a": "UUID-A",
  "item_id_b": "UUID-B",
  "compare_mode": "summarized",
  "levels": -1,
  "include_unchanged": false,
  "format": "csv",
  "columns": ["key", "status", "child_id", "name", "qty_a", "qty_b", "delta"],
  "exclude_columns": ["refdes_a", "refdes_b"],
  "delimiter": ",",
  "filename": "bom_compare.csv",
  "diff_only": true,
  "xlsx_sheet_mode": "combined"
}
```

Response:
- CSV or XLSX file stream (set `format` to `xlsx` for Excel output; requires `openpyxl`)
- Summary counts in headers:
  - `X-BOM-Compare-Added`
  - `X-BOM-Compare-Removed`
  - `X-BOM-Compare-Modified`
  - `X-BOM-Compare-Unchanged`

## Pack-and-Go Plugin

Base path: `/api/v1/plugins/pack-and-go`

### Sync Pack

`POST /`

Request:
```json
{
  "item_id": "UUID-A",
  "depth": -1,
  "relationship_types": ["Part BOM"],
  "export_type": "all",
  "filename_mode": "original",
  "filename_template": "{item_number}_{revision}{original_ext}",
  "path_strategy": "item_role",
  "collision_strategy": "append_id",
  "file_scope": "item",
  "file_roles": ["native_cad", "attachment", "printout", "geometry", "drawing"],
  "document_types": ["2d", "3d", "pr", "other"],
  "include_item_types": ["Part", "Document"],
  "exclude_item_types": [],
  "include_item_ids": [],
  "exclude_item_ids": [],
  "allowed_states": ["Released"],
  "blocked_states": ["Obsolete"],
  "allowed_extensions": ["step", "pdf"],
  "blocked_extensions": ["tmp"],
  "include_previews": false,
  "include_printouts": true,
  "include_geometry": true,
  "include_bom_tree": false,
  "bom_tree_filename": "bom_tree.json",
  "include_manifest_csv": false,
  "manifest_csv_filename": "manifest.csv",
  "manifest_csv_columns": ["file_id", "filename", "file_role", "source_item_number"],
  "include_bom_flat": false,
  "bom_flat_format": "csv",
  "bom_flat_filename": "bom_flat.csv",
  "bom_flat_columns": ["level", "parent_id", "child_id", "quantity"],
  "async": false
}
```

Response: ZIP file stream (includes `manifest.json`).
Optional extras when enabled:
- `bom_tree.json` (set `include_bom_tree=true`)
- `manifest.csv` (set `include_manifest_csv=true`)

Notes:
- `export_type` presets: `all`, `2d`, `3d`, `pdf`, `2dpdf`, `3dpdf`, `3d2d` (separators like `2d+pdf` are accepted).
- When `export_type` is set, defaults for `file_roles`, `document_types`, `include_printouts`, `include_geometry` are applied unless those fields are explicitly provided.
- `filename_mode` options: `original`, `item_number`, `item_number_rev`, `internal_ref` (`item_number_rev` uses item properties or `current_version_id` when available).
- `filename_template` overrides `filename_mode` and supports placeholders like `{item_number}`, `{revision}`, `{file_role}`, `{original_ext}`.
- `path_strategy` options: `item_role`, `item`, `role`, `flat`, `document_type`, `item_document_type`, `role_document_type`, `item_role_document_type`.
- `collision_strategy` options: `append_id` (default), `append_counter`, `error`.
- `file_scope` options: `item` (ItemFile links) or `version` (VersionFile links with fallback to item files).
- Filters: `include_item_types`, `exclude_item_types`, `allowed_states`, `allowed_extensions`, etc. are applied before packaging.
- `include_bom_flat` can add a flat BOM CSV/JSONL export; `bom_flat_columns` controls CSV ordering.
- `manifest_csv_columns` allows CSV column selection and ordering (extra fields like `file_extension` and `item_revision` are available).
- Manifest file entries include `output_filename` (final name after naming mode/collision).

### Async Pack (optional)

`POST /` with `async=true` returns a job id:
```json
{"ok": true, "job_id": "...", "status_url": "..."}
```

Check status:
- `GET /jobs/{job_id}`

Download when complete:
- `GET /jobs/{job_id}/download`

## Pack-and-Go Configuration

```bash
export YUANTUS_PACKGO_OUTPUT_DIR=./tmp/pack_and_go
export YUANTUS_PACKGO_MAX_FILES=2000
export YUANTUS_PACKGO_MAX_BYTES=0
export YUANTUS_PACKGO_RETENTION_MINUTES=30
export YUANTUS_PACKGO_CACHE_ENABLED=false
export YUANTUS_PACKGO_CACHE_TTL_MINUTES=60
export YUANTUS_PACKGO_PROGRESS_INTERVAL=50
```

## Worker Support for Async Pack

The CLI worker now attempts to register plugin job handlers if they expose
`register_job_handlers(worker)`. For this plugin, the task type is `pack_and_go`.

Start worker:
```bash
yuantus worker
```

## Plugin Config API

Per-tenant plugin config can be stored via:
- `GET /api/v1/plugins/{plugin_id}/config`
- `PUT /api/v1/plugins/{plugin_id}/config`

Update request:
```json
{
  "config": {"default_export_type": "3d", "cache_enabled": true},
  "merge": true
}
```

## Tests

Run plugin unit tests:
```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py
```
