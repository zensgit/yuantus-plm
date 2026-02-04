# Endpoint Change Log (2026-02-02)

## Added

### Reports
- `POST /api/v1/reports/definitions/{report_id}/export`
  - Export report data in `csv` or `json`.
  - Body: `{ page, page_size, export_format, parameters }`

- `GET /api/v1/reports/executions`
  - List report executions.
  - Query: `report_id`, `status`, `limit`, `offset`

- `GET /api/v1/reports/executions/{execution_id}`
  - Get report execution details.

### Baselines
- `GET /api/v1/baselines/effective`
  - Resolve released baseline effective at a target date.
  - Query: `root_item_id`, `target_date`, `baseline_type`, `include_snapshot`

- `GET /api/v1/baselines/comparisons/{comparison_id}/details`
  - Paginated comparison details.
  - Query: `change_type=added|removed|changed`, `limit`, `offset`

- `GET /api/v1/baselines/comparisons/{comparison_id}/export`
  - Export comparison details in `csv` or `json`.
  - Query: `change_type`, `export_format`, `limit`, `offset`

### BOM
- `GET /api/v1/bom/{item_id}/obsolete`
  - Scan BOM for obsolete relationships and replacements.
  - Query: `recursive`, `max_levels`

- `POST /api/v1/bom/{item_id}/obsolete/resolve`
  - Resolve BOM obsolete replacements (preview or apply).
  - Body: `{ apply, mode, relationship_types, candidates, replacement_properties, copy_properties }`

- `POST /api/v1/bom/{item_id}/rollup/weight`
  - Compute BOM weight rollup (optionally write back).
  - Body: `{ levels, effective_at, rounding, write_back, write_back_field, dry_run }`

### Product Detail
- `GET /api/v1/products/{item_id}`
  - Extended summary query options for BOM obsolete and weight rollup.
  - Query: `include_bom_obsolete_summary`, `bom_obsolete_recursive`, `bom_obsolete_levels`,
    `include_bom_weight_rollup`, `bom_weight_levels`, `bom_weight_effective_at`, `bom_weight_rounding`

### Electronic Signatures
- `PATCH /api/v1/esign/reasons/{reason_id}`
  - Update signing reasons (including activate/deactivate).
  - Body: `{ code, name, meaning, description, regulatory_reference, requires_password, requires_comment, item_type_id, from_state, to_state, sequence, is_active }`

- `GET /api/v1/esign/audit-logs`
  - Query audit logs.
  - Query: `item_id`, `signature_id`, `actor_id`, `action`, `success`, `date_from`, `date_to`, `limit`, `offset`

- `GET /api/v1/esign/audit-summary`
  - Summary counts by action/success.
  - Query: `item_id`, `signature_id`, `actor_id`, `action`, `success`, `date_from`, `date_to`

- `GET /api/v1/esign/audit-logs/export`
  - Export audit logs in `csv` or `json`.
  - Query: `export_format`, plus filters above.

## Notes

- Report definition access now enforces `allowed_roles` for public reports.
- Export endpoints default to `csv` if not specified.
- Advanced search filters now include `startswith`, `endswith`, and `not_contains`.
