# Verification Report (2026-01-09)

## Audit Logs
- Command: `bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1`
- Result: ALL CHECKS PASSED
- Evidence: audit log entry for `/api/v1/health` returned via `/api/v1/admin/audit`.

## Quota Enforcement
- Command: `bash scripts/verify_quotas.sh http://127.0.0.1:7910 tenant-1 org-1`
- Result: ALL CHECKS PASSED
- Checks: org, user, file, and job quota blocks returned HTTP 429 after limits applied.

## CAD Real Samples
- Command: `bash scripts/verify_cad_real_samples.sh http://127.0.0.1:7910 tenant-1 org-1`
- Result: ALL CHECKS PASSED
- Samples: default CAD_SAMPLE_DWG/STEP/PRT values from `scripts/verify_cad_real_samples.sh`.
- Imported items:
  - DWG: file_id=b0a5a735-ff1f-4e9f-a12e-8f50918c9496, item_id=d1ff77a4-8eb3-42b0-9849-579d8cda6b1d
  - STEP: file_id=36c71d40-b699-4244-8daf-3371ac041cf4, item_id=cee290db-5d06-49c6-a235-9df1d8ea692b
  - PRT: file_id=4e56b06e-cb3e-470a-8736-c0f75583fd81, item_id=3e6fa7a2-9b78-434a-bdd4-745705c4e643

## CI
- Regression workflow triggered: https://github.com/zensgit/yuantus-plm/actions/runs/20855673195
- Status at report time: completed (success)
