# Verification - Docs + Approval (2026-01-09)

## Environment

- Base URL: http://127.0.0.1:7910
- Tenant: tenant-1
- Org: org-1
- Script: `scripts/verify_docs_approval.sh`

## Command

```bash
bash scripts/verify_docs_approval.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Results

- Status: ALL CHECKS PASSED
- Document Part ID: 0ed37e75-bb21-40f4-887e-03b1841bba3a
- Document File ID: c82f2c24-f77a-4311-adc3-360a127dfed7
- Document Item ID: 2b80bf85-2952-402a-810d-756c1dcc16a9
- Approval Stage ID: 736bdb73-60a7-4f73-a169-2974281c595e
- ECO Product ID: 1311ed54-0291-4490-9df9-b8eac7df5958
- ECO ID: 753f375d-8bcd-4cb4-8d16-c89f000c340f
- Approval ID: 30aa6948-c8f2-4707-8945-a3e5dbd976a3

## Notes

- Document upload/metadata/attachment verified.
- Document lifecycle enforced Draft → Review → Released with lock checks.
- ECO approval flow confirmed (stage move → approve → state=approved).
