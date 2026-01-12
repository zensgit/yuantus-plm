# Plugin Enhancements Dev Log

## Scope

This update extends the BOM Compare and Pack-and-Go plugins plus introduces a
per-tenant plugin config API.

## Pack-and-Go

- Added `filename_template`, `file_scope`, new `path_strategy` variants, and
  item/file filters (`include_item_types`, `allowed_states`, `allowed_extensions`, etc.).
- Added optional flat BOM export (`include_bom_flat`, `bom_flat_format`, `bom_flat_columns`).
- Added manifest CSV column selection (`manifest_csv_columns`) and richer manifest fields.
- Added async job progress updates, structured logs, and cache support.
- Fixed `file_scope=version` mapping so version-scoped exports resolve item IDs
  from VersionFile records correctly.

Key files:
- `plugins/yuantus-pack-and-go/main.py`
- `docs/PLUGIN_BOM_PACK_AND_GO.md`

## BOM Compare

- Added `quantity_tolerance` and diff filters (`filters`) with regex and delta bounds.
- Added export options (`exclude_columns`, `diff_only`, `xlsx_sheet_mode`).
- Added apply preview mode (`preview=true`).

Key files:
- `plugins/yuantus-bom-compare/main.py`
- `docs/PLUGIN_BOM_PACK_AND_GO.md`

## Plugin Config API

- Added `meta_plugin_configs` table and service layer.
- Added REST endpoints:
  - `GET /api/v1/plugins/{plugin_id}/config`
  - `PUT /api/v1/plugins/{plugin_id}/config`
- Plugin manifests now expose `config_schema` and `capabilities`.

Key files:
- `src/yuantus/meta_engine/models/plugin_config.py`
- `src/yuantus/meta_engine/services/plugin_config_service.py`
- `src/yuantus/api/routers/plugins.py`
- `src/yuantus/plugin_manager/plugin_manager.py`
- `plugins/yuantus-pack-and-go/plugin.json`
- `plugins/yuantus-bom-compare/plugin.json`
- `migrations/versions/m1b2c3d4e6a1_add_plugin_configs.py`

## Configuration

Pack-and-Go env vars:
- `YUANTUS_PACKGO_CACHE_ENABLED`
- `YUANTUS_PACKGO_CACHE_TTL_MINUTES`
- `YUANTUS_PACKGO_PROGRESS_INTERVAL`

See `docs/PLUGIN_BOM_PACK_AND_GO.md` for full request schemas and examples.

## Tests

Run:
```bash
pytest -q src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py
```
