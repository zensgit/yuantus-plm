# CAD Verification Summary (Recent Runs)

This document aggregates the most recent CAD-related verification runs and outputs for delivery use.

## Environment

- Base URL: `http://127.0.0.1:7910`
- Tenant/Org: `tenant-1` / `org-1`
- Tenancy: `db-per-tenant-org`
- Database: `postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
- DB Template: `postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
- Identity DB: `postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`
- Storage: `s3` (MinIO)
- S3 Endpoint: `http://localhost:59000`

## Verified Areas (All Passed)

### 1) CAD Connectors

- 2D connectors: `scripts/verify_cad_connectors_2d.sh`
- 3D connectors: `scripts/verify_cad_connectors_3d.sh`
- 2D real samples: `scripts/verify_cad_connectors_real_2d.sh`
- Evidence: `docs/VERIFICATION_RESULTS.md`

### 2) CAD Attribute Flow

- Attribute normalization: `scripts/verify_cad_attribute_normalization.sh`
- Filename parsing: `scripts/verify_cad_filename_parse.sh`
- Local extract: `scripts/verify_cad_extract_local.sh`
- Attribute sync: `scripts/verify_cad_sync.sh`
- Auto part: `scripts/verify_cad_auto_part.sh`
- Evidence: `docs/VERIFICATION_RESULTS.md`

### 3) S3 CAD Pipeline

- Preview/geometry pipeline: `scripts/verify_cad_pipeline_s3.sh`
- Preview API: `scripts/verify_cad_preview_2d.sh`
- Missing source failure: `scripts/verify_cad_missing_source.sh`
- Evidence: `docs/VERIFICATION_RESULTS.md`

### 4) CAD Extractor Service

- Service health: `scripts/verify_cad_extractor_service.sh`
- External integration: `scripts/verify_cad_extractor_external.sh`
- Stub integration: `scripts/verify_cad_extractor_stub.sh`
- Evidence: `docs/VERIFICATION_RESULTS.md`

### 5) Connector Coverage

- Offline coverage reports: `scripts/verify_cad_connector_coverage_2d.sh`
- Outputs:
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_HAOCHEN.md`
  - `docs/CAD_CONNECTORS_COVERAGE_TRAINING_DWG_ZHONGWANG.md`

## Notes

- Some runs emit `cadquery not installed`. This does not affect the current pass criteria.
- Full commands and IDs are recorded in `docs/VERIFICATION_RESULTS.md`.
