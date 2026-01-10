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
  "include_unchanged": false
}
```

Response:
```json
{
  "summary": {"added": 1, "removed": 0, "modified": 2, "unchanged": 10},
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
  "dry_run": false
}
```

Notes:
- `add` validates cycle detection and uses AML relationship add.
- `update/remove` require relationship item ids.
- Permissions are enforced by AML.

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
  "delimiter": ",",
  "filename": "bom_compare.csv"
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
  "file_roles": ["native_cad", "attachment", "printout", "geometry", "drawing"],
  "document_types": ["2d", "3d", "pr", "other"],
  "include_previews": false,
  "include_printouts": true,
  "include_geometry": true,
  "include_bom_tree": false,
  "bom_tree_filename": "bom_tree.json",
  "include_manifest_csv": false,
  "manifest_csv_filename": "manifest.csv",
  "async": false
}
```

Response: ZIP file stream (includes `manifest.json`).
Optional extras when enabled:
- `bom_tree.json` (set `include_bom_tree=true`)
- `manifest.csv` (set `include_manifest_csv=true`)

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
```

## Worker Support for Async Pack

The CLI worker now attempts to register plugin job handlers if they expose
`register_job_handlers(worker)`. For this plugin, the task type is `pack_and_go`.

Start worker:
```bash
yuantus worker
```

## Tests

Run plugin unit tests:
```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py
```
