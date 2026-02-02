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

## 4) E-sign Audit Logs

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
