# Verification - BOM UI Endpoints (2026-01-09)

## Environment

- Base URL: http://127.0.0.1:7910
- Tenant: tenant-1
- Org: org-1
- Script: `scripts/verify_bom_ui.sh`

## Command

```bash
bash scripts/verify_bom_ui.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Results

- Status: ALL CHECKS PASSED
- Substitute relation ID: 93720da1-465f-49e0-9eae-319dfe156eba

## Notes

- Verified where-used returns parent item_number.
- Verified BOM compare returns child fields when `include_child_fields=true`.
- Verified substitute listing includes substitute part metadata.
