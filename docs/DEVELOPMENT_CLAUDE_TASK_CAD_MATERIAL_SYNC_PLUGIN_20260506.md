# Development Task - CAD Material Sync Plugin

Date: 2026-05-06

## 1. Goal

Add a server-side plugin that lets CAD clients translate material-related title
block or BOM-table fields into PLM item properties, compose material
specifications, validate required fields, and return a CAD field package for
write-back.

This slice is intentionally server-side. It exposes the plugin API and default
profiles, but it does not ship a compiled AutoCAD/SolidWorks client.

## 2. Scope

- Add plugin manifest and FastAPI router under `plugins/yuantus-cad-material-sync/`.
- Support default material profiles for sheet, tube, bar, and forging.
- Support profile overrides through existing `PluginConfigService`.
- Compose `specification` from source fields while preserving those source
  fields as independent properties.
- Convert CAD field names to PLM property names and PLM properties back to CAD
  field packages.
- Support outbound PLM-to-CAD field package generation.
- Support inbound CAD-to-PLM dry-run, conflict detection, optional update, and
  optional create.
- Add focused plugin unit/API tests and plugin runtime smoke coverage.

## 3. API Surface

- `GET /api/v1/plugins/cad-material-sync/profiles`
- `GET /api/v1/plugins/cad-material-sync/profiles/{profile_id}`
- `POST /api/v1/plugins/cad-material-sync/compose`
- `POST /api/v1/plugins/cad-material-sync/validate`
- `POST /api/v1/plugins/cad-material-sync/sync/outbound`
- `POST /api/v1/plugins/cad-material-sync/sync/inbound`

## 4. Design

Profiles define:

- `fields`: logical property names, CAD field names, labels, required state,
  type, unit, and defaults.
- `compose`: target property and format template.
- `cad_mapping`: PLM property to CAD field-name output mapping.
- `selector`: default classification properties such as material category.

The plugin keeps `specification` as a derived/cache field. Source dimensions
such as length, width, thickness, outer diameter, wall thickness, diameter, and
blank size remain separate properties so future search, matching, unit
conversion, and impact analysis are not forced to parse a display string.

Inbound sync defaults to non-destructive behavior:

- blank target fields may be filled;
- matching existing values are ignored;
- conflicting existing values are returned as conflicts;
- overwrite requires explicit `overwrite=true` or profile `sync_defaults.overwrite=true` when the request omits `overwrite`;
- request-level `overwrite=false/true` always takes precedence over profile defaults;
- item creation requires explicit `create_if_missing=true`;
- dry run is available through `dry_run=true`.

## 5. Non-Goals

- No database migration.
- No PLM core router registration change.
- No direct DWG/DXF mutation on the server.
- No compiled AutoCAD or SolidWorks client artifact.
- No management UI for editing profiles.
- No production rollout or tenant-specific profile enablement.

## 6. Verification

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q

PYTHONPATH=src YUANTUS_PLUGINS_ENABLED=yuantus-cad-material-sync python3 -c \
  "from fastapi import FastAPI; from yuantus.plugin_manager.runtime import load_plugins; app=FastAPI(); manager=load_plugins(app); print(manager.get_plugin_stats() if manager else None); print(sorted(getattr(route, 'path', '') for route in app.routes if 'cad-material-sync' in getattr(route, 'path', '')))"

PYTHONPATH=src python3 -m pytest \
  src/yuantus/api/tests/test_plugin_runtime_security.py \
  src/yuantus/meta_engine/tests/test_plugin_bom_compare.py \
  src/yuantus/meta_engine/tests/test_plugin_pack_and_go.py \
  src/yuantus/meta_engine/tests/test_cad_properties_router.py \
  src/yuantus/meta_engine/tests/test_cad_sync_template_router.py \
  src/yuantus/meta_engine/tests/test_cad_import_service.py \
  src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py -q
```
