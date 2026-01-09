# Verification - CAD Connectors (2026-01-09)

## Environment

- Base URL: http://127.0.0.1:7910
- Tenant: tenant-1
- Org: org-1
- Script: `scripts/verify_cad_connectors.sh`
- Real samples: skipped (RUN_REAL=0)

## Command

```bash
bash scripts/verify_cad_connectors.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Results

- Status: ALL CHECKS PASSED
- GStarCAD file_id: eabb10de-ab53-47d1-817a-359f0e609332
- ZWCAD file_id: dff29d89-1aef-4aed-92c2-efac413272b8
- Haochen file_id: 10bc1151-2920-40e3-b21a-7557f5aa5e8a
- Zhongwang file_id: 5531ccc1-5f47-46a2-83c3-91898f558ffe
- Auto-detect (Haochen) file_id: b5846a9a-5c0b-4b0a-a7d8-7b9d51d8ffbe
- Auto-detect (ZWCAD) file_id: cdcfb7c2-1c26-4686-82da-77ad963f5790

## Notes

- Verified `cad_format`, `cad_connector_id`, and `document_type=2d` for 2D connectors.
- Real sample validation can be enabled with `RUN_REAL=1`.
