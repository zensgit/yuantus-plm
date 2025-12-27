# CAD Connector Framework (YuantusPLM)

## Goals

- Provide a consistent way to identify CAD vendors/formats and document type (2D/3D).
- Allow explicit vendor overrides during `/cad/import` (e.g., `GSTARCAD`, `ZWCAD`).
- Offer a registry to plug in vendor-specific extraction and future BOM/metadata sync.

## Components

- `cad_connectors.base`
  - `CadConnectorInfo`: connector metadata (id, label, cad_format, document_type, extensions, aliases, priority, signature_tokens).
  - `CadConnector`: base interface for matching and attribute extraction.
  - `StaticCadConnector`: simple connector with static attributes.

- `cad_connectors.registry`
  - `CadConnectorRegistry`: register/list/resolve connectors by format or extension.
  - `CadResolvedMetadata`: resolved `cad_format` + `document_type`.

- `cad_connectors.builtin`
  - Built-in connectors for common formats and vendors (AutoCAD, GStarCAD, ZWCAD, Haochen CAD, Zhongwang CAD, STEP, IGES, etc.).
  - Haochen CAD: `cad_format=HAOCHEN`, `connector_id=haochencad`.
  - Zhongwang CAD: `cad_format=ZHONGWANG`, `connector_id=zhongwangcad`.
  - Priority determines default for shared extensions (e.g., DWG/DXF -> AutoCAD unless overridden).
  - 2D connectors use a key-value extractor for quick attribute sync in dev/demo.
  - Key-value aliases include common Chinese field labels (e.g., 图号/零件号/名称/材料/版本/重量).

## 3D Connector Defaults (Priority Order)

- SolidWorks: `cad_format=SOLIDWORKS`, `connector_id=solidworks`, extensions `sldprt/sldasm`.
- NX: `cad_format=NX`, `connector_id=nx`, extensions `prt/asm` (default for `.prt/.asm`).
- Creo: `cad_format=CREO`, `connector_id=creo`, extensions `prt/asm`.
- CATIA: `cad_format=CATIA`, `connector_id=catia`, extensions `catpart/catproduct`.
- Inventor: `cad_format=INVENTOR`, `connector_id=inventor`, extensions `ipt/iam`.

Notes:
- NX/Creo share extensions; use `cad_format=CREO`, `cad_connector_id=creo`, or `source_system=Creo` to force Creo.
- Legacy alias `cad_format=NX_OR_PROE` remains for backward compatibility.

## 3D Attribute Keys (Recommended)

The extractor should return these keys (map via `is_cad_synced` + `ui_options.cad_key`):

- `part_number`
- `part_name`
- `material`
- `weight`
- `revision`
- `drawing_no`
- `author`
- `created_at`

## Integration Points

- `/api/v1/cad/import`
  - Uses the registry to resolve `cad_format` and `document_type`.
  - Supports explicit overrides via `cad_format` or `cad_connector_id` form fields.
  - Supports `auto_create_part=true` to create/link a Part when `item_id` is missing.
  - If no override is provided, tries to auto-detect vendor by content/filename signature tokens.
  - Auto-detection scoring favors connectors with more matched tokens, longer token hits, then priority.
  - Persists `cad_connector_id` on the file metadata for downstream sync.
- `/api/v1/cad/connectors`
  - Lists available connectors and their capabilities.
- `/api/v1/cad/files/{file_id}/attributes`
  - Returns the latest `cad_extract` job result for the file.
  - Attributes are persisted on the file metadata (`meta_files.cad_attributes`).

- `CadService.extract_attributes`
  - Delegates to a connector when available.
  - Falls back to the current simulation when no connector returns attributes.
- `CadService.sync_attributes_to_item`
  - Writes CAD attributes only into fields flagged with `is_cad_synced`.
  - Optional mapping via `ui_options.cad_key`.

## CAD Extractor (Optional External Service)

You can point Yuantus to an external extractor service:

Environment variables:
- `YUANTUS_CAD_EXTRACTOR_BASE_URL`
- `YUANTUS_CAD_EXTRACTOR_SERVICE_TOKEN` (optional)
- `YUANTUS_CAD_EXTRACTOR_TIMEOUT_SECONDS`
- `YUANTUS_CAD_EXTRACTOR_MODE` (`optional`|`required`)
 - `CAD_EXTRACTOR_SAMPLE_FILE` (for verification script)

Expected API (example):
- `POST /api/v1/extract` (multipart form)
  - file: CAD file
  - cad_format: optional
  - cad_connector_id: optional
  - response: `{ "ok": true, "attributes": { ... } }`

If `CAD_EXTRACTOR_MODE=required`, any extractor failure will fail the `cad_extract` job.

Reference implementation (in this repo):
- `services/cad-extractor` (FastAPI microservice)
- Start with Docker:
  - `docker compose up -d cad-extractor`
  - or standalone: `docker compose -f docker-compose.cad-extractor.yml up -d`
- Point Yuantus to it:
  - Compose (API/Worker in containers): `http://cad-extractor:8200`
  - Local dev: `http://localhost:8200`
- Includes filename parsing for `part_number`, `description`, and `revision` when present in the stem.

## Custom Connector Config

Load extra connectors from a JSON config file (without changing code):

- Env: `YUANTUS_CAD_CONNECTORS_CONFIG_PATH=/path/to/cad_connectors.json`
- Optional (admin only): `POST /api/v1/cad/connectors/reload`
  - JSON body can include `config` (inline) or `config_path` (file path).
  - `config_path` requires `YUANTUS_CAD_CONNECTORS_ALLOW_PATH_OVERRIDE=true`.

Sample config: `docs/CAD_CONNECTORS_CONFIG_TEMPLATE.json`

Notes:
- Custom connectors are registered after built-ins.
- Set `priority` to override format/extension matching.
- Set `override=true` to replace a built-in connector with the same `id`.
- Versioned filenames like `part.prt.1` or `assembly.asm.18` are treated as CAD files by resolving the second-to-last extension.

## CAD Sync Template

Download or apply a CAD attribute sync template for an ItemType:

- `GET /api/v1/cad/sync-template/{item_type_id}?output_format=csv|json`
- `POST /api/v1/cad/sync-template/{item_type_id}` (CSV upload)

CSV columns:
- `property_name`
- `label`
- `data_type`
- `is_cad_synced`
- `cad_key`

## How to Add a New Connector

1) Create a connector in `src/yuantus/integrations/cad_connectors/builtin.py`:

```python
registry.register(
    build_simple_connector(
        connector_id="megacad",
        label="MegaCAD",
        cad_format="MEGACAD",
        document_type="3d",
        extensions=["mcd"],
        aliases=["MEGA"],
        priority=10,
    )
)
```

2) If you need custom extraction, subclass `CadConnector` and implement `extract_attributes`.

## Roadmap (Next)

- Connector-specific BOM extraction and part metadata mapping.
- Connector capabilities endpoint (BOM/preview/metadata support).
- Per-connector conversion pipelines and external SDK adapters.
