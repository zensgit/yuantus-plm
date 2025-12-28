# CAD Verification Matrix

This matrix lists CAD verification scripts and their runtime dependencies.

Legend:
- API: Yuantus API server (`yuantus start`)
- DB: database connectivity (Postgres/SQLite depending on script)
- Storage: `local` or `s3` (MinIO)
- CAD ML: CAD ML service (`http://localhost:8001`)
- Extractor: CAD Extractor service (`http://localhost:8200`)

| Script | Purpose | API | DB | Storage | CAD ML | Extractor | Samples/Inputs | Output |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scripts/verify_cad_connectors_2d.sh` | 2D connector detection/import | Yes | Required | Local or S3 | No | No | Auto-generated DWG/DXF | IDs in `docs/VERIFICATION_RESULTS.md` |
| `scripts/verify_cad_connectors_3d.sh` | 3D connector detection/import | Yes | Required | Local or S3 | No | No | Auto-generated 3D files | IDs in `docs/VERIFICATION_RESULTS.md` |
| `scripts/verify_cad_connectors_real_2d.sh` | 2D real DWG samples | Yes | Required | Local or S3 | No | Optional | Requires real DWG files | IDs in `docs/VERIFICATION_RESULTS.md` |
| `scripts/verify_cad_preview_2d.sh` | DWG preview rendering | Yes | Required | Local or S3 | Yes | No | DWG file path | HTTP 200/302 |
| `scripts/verify_cad_real_samples.sh` | Real DWG/STEP/PRT full flow | Yes | Required | Local or S3 | Optional | Optional | Sample DWG/STEP/PRT files | IDs in `docs/VERIFICATION_RESULTS.md` |
| `scripts/verify_cad_sync.sh` | CAD attribute sync to Item | Yes | Required | Local or S3 | No | Optional | Auto DWG (or file path) | Item properties updated |
| `scripts/verify_cad_auto_part.sh` | Auto-create Part on import | Yes | Required | Local or S3 | No | Optional | Auto DWG (or file path) | Part/File/Attachment IDs |
| `scripts/verify_cad_sync_template.sh` | Sync template export/import | Yes | Required | Any | No | No | Template CSV | Properties updated |
| `scripts/verify_cad_connectors_config.sh` | Reload connectors from JSON | Yes | Required | Any | No | No | Inline JSON config | Connector list + import OK |
| `scripts/verify_cad_pipeline_s3.sh` | Preview/geometry pipeline | Yes | Required | S3 recommended | Optional | No | Auto STL | 302 to presigned URL |
| `scripts/verify_cad_missing_source.sh` | Missing source job failure | Yes | Required | Local or S3 | Optional | No | Auto DWG | Job fails without retry |
| `scripts/verify_cad_extractor_stub.sh` | External extractor stub | Yes | Required | Local or S3 | No | Stub | Auto DWG | `source=external` |
| `scripts/verify_cad_extractor_external.sh` | External extractor integration | Yes | Required | Local or S3 | No | Yes | DWG sample | `source=external` |
| `scripts/verify_cad_extractor_service.sh` | Extractor service health | No | No | No | No | Yes | None | Extractor OK |
| `scripts/verify_cad_attribute_normalization.sh` | Attribute normalization | No | SQLite | Local | No | No | Inline text | PASS/FAIL |
| `scripts/verify_cad_filename_parse.sh` | Filename parsing | No | SQLite | Local | No | No | Inline samples | PASS/FAIL |
| `scripts/verify_cad_extract_local.sh` | Local extract task | No | SQLite | Local | No | No | Inline text | PASS/FAIL |
| `scripts/verify_cad_connector_coverage_2d.sh` | Offline DWG coverage report | No | SQLite | Local | No | No | `CAD_CONNECTOR_COVERAGE_DIR` | Coverage reports |

Notes:
- When `TENANCY_MODE=db-per-tenant-org`, pass `DB_URL_TEMPLATE` and `TENANCY_MODE_ENV` to scripts.
- `scripts/verify_cad_pipeline_s3.sh` returns PARTIAL SUCCESS on local storage; full PASS expects S3 redirects.
