# Delivery API Examples (2026-02-02)

Base URL examples below use `http://127.0.0.1:7910`.

## 1) Report Export (CSV/JSON)

```bash
# CSV (default)
curl -s -X POST \
  http://127.0.0.1:7910/api/v1/reports/definitions/{report_id}/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"page":1,"page_size":500,"export_format":"csv"}' \
  -o report.csv

# JSON
curl -s -X POST \
  http://127.0.0.1:7910/api/v1/reports/definitions/{report_id}/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"page":1,"page_size":500,"export_format":"json"}' \
  -o report.json
```

## 2) Report Executions

```bash
# List executions for a report
curl -s \
  "http://127.0.0.1:7910/api/v1/reports/executions?report_id={report_id}&limit=100&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Get execution by id
curl -s \
  "http://127.0.0.1:7910/api/v1/reports/executions/{execution_id}" \
  -H "Authorization: Bearer $TOKEN"
```

## 3) Baseline Comparison Details

```bash
# All changes (paginated)
curl -s \
  "http://127.0.0.1:7910/api/v1/baselines/comparisons/{comparison_id}/details?limit=200&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Only changed items
curl -s \
  "http://127.0.0.1:7910/api/v1/baselines/comparisons/{comparison_id}/details?change_type=changed&limit=200&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Export comparison details
curl -s \
  "http://127.0.0.1:7910/api/v1/baselines/comparisons/{comparison_id}/export?change_type=changed&export_format=csv" \
  -H "Authorization: Bearer $TOKEN" \
  -o comparison.csv
```

## 4) Baseline Effective Date

```bash
# Resolve the released baseline that was effective at a specific date
curl -s \
  "http://127.0.0.1:7910/api/v1/baselines/effective?root_item_id={root_item_id}&target_date=2025-12-31T00:00:00Z&baseline_type=design" \
  -H "Authorization: Bearer $TOKEN"
```

## 4.1) Baseline List Filters

```bash
# Filter baselines by type/scope/state and effective date range
curl -s \
  "http://127.0.0.1:7910/api/v1/baselines?baseline_type=design&scope=product&state=released&effective_from=2025-01-01T00:00:00Z&effective_to=2025-12-31T23:59:59Z&limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

## 4.2) Effectivity (Lot/Serial)

```bash
# Create lot-based effectivity for a BOM relationship item
curl -s -X POST \
  "http://127.0.0.1:7910/api/v1/effectivities" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_id":"{relationship_id}","effectivity_type":"Lot","payload":{"lot_start":"L010","lot_end":"L020"}}'

# Create serial-based effectivity
curl -s -X POST \
  "http://127.0.0.1:7910/api/v1/effectivities" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_id":"{relationship_id}","effectivity_type":"Serial","payload":{"serials":["SN-1","SN-2"]}}'

# Query BOM with lot/serial filtering
curl -s \
  "http://127.0.0.1:7910/api/v1/bom/{parent_id}/effective?lot_number=L015&serial_number=SN-1&levels=1" \
  -H "Authorization: Bearer $TOKEN"
```

## 4.3) BOM Obsolete Scan + Resolve

```bash
# Scan obsolete lines under a root item (direct + recursive)
curl -s \
  "http://127.0.0.1:7910/api/v1/bom/{parent_id}/obsolete?recursive=true&levels=10" \
  -H "Authorization: Bearer $TOKEN"

# Resolve in-place (update child to replacement_id)
curl -s -X POST \
  "http://127.0.0.1:7910/api/v1/bom/{parent_id}/obsolete/resolve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"update"}'

# Resolve by cloning a new BOM set
curl -s -X POST \
  "http://127.0.0.1:7910/api/v1/bom/{parent_id}/obsolete/resolve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"new_bom","recursive":true,"levels":10}'
```

Notes:
- Add `"dry_run": true` to preview the plan without applying changes.
- Use `relationship_types` to limit scan/resolve to `Part BOM` or `Manufacturing BOM`.
- `new_bom` creates new BOM lines and marks old lines `is_current=false` so you can revert by reactivating old lines if needed.

## 4.4) BOM Weight Rollup

```bash
# Compute rollup only
curl -s -X POST \
  "http://127.0.0.1:7910/api/v1/bom/{parent_id}/rollup/weight" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"levels":3}'

# Compute and write back to properties.weight_rollup (missing only)
curl -s -X POST \
  "http://127.0.0.1:7910/api/v1/bom/{parent_id}/rollup/weight" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"levels":3,"write_back":true,"write_back_field":"weight_rollup","write_back_mode":"missing","rounding":3}'
```

Notes:
- `write_back_mode=missing` only writes when `weight` is missing; use `overwrite` to always write.
- `write_back_field` defaults to `weight_rollup`.
- Locked lifecycle states are skipped and reported as `skipped_locked` in the updates list.

## 4.5) Product Detail BOM Summary Extensions

```bash
# Fetch product detail with obsolete + rollup summaries
curl -s \
  "http://127.0.0.1:7910/api/v1/products/{item_id}?include_bom_obsolete_summary=true&include_bom_weight_rollup=true&bom_weight_levels=3" \
  -H "Authorization: Bearer $TOKEN"
```

## 5) E-sign Audit Logs

```bash
# Logs for an item
curl -s \
  "http://127.0.0.1:7910/api/v1/esign/audit-logs?item_id={item_id}&limit=200&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Logs for a signature
curl -s \
  "http://127.0.0.1:7910/api/v1/esign/audit-logs?signature_id={signature_id}" \
  -H "Authorization: Bearer $TOKEN"

# Audit summary
curl -s \
  "http://127.0.0.1:7910/api/v1/esign/audit-summary?item_id={item_id}" \
  -H "Authorization: Bearer $TOKEN"

# Export audit logs
curl -s \
  "http://127.0.0.1:7910/api/v1/esign/audit-logs/export?export_format=csv&item_id={item_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -o audit.csv
```

## 6) E-sign Reason Update

```bash
curl -s -X PATCH \
  "http://127.0.0.1:7910/api/v1/esign/reasons/{reason_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Approved (Final)","is_active":false}'
```

## 7) Advanced Search Filter Ops

```bash
# startswith / endswith / not_contains
curl -s -X POST \
  http://127.0.0.1:7910/api/v1/reports/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": [
      {"field": "config_id", "op": "startswith", "value": "ASSY"},
      {"field": "config_id", "op": "endswith", "value": "-A"},
      {"field": "config_id", "op": "not_contains", "value": "TMP"}
    ],
    "page": 1,
    "page_size": 50
  }'
```
