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
- `GET /api/v1/baselines/comparisons/{comparison_id}/details`
  - Paginated comparison details.
  - Query: `change_type=added|removed|changed`, `limit`, `offset`

- `GET /api/v1/baselines/comparisons/{comparison_id}/export`
  - Export comparison details in `csv` or `json`.
  - Query: `change_type`, `export_format`, `limit`, `offset`

### Electronic Signatures
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
