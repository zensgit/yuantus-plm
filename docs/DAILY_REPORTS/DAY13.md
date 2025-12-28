# Day 13 - Regression Hardening (RBAC + Cad Sync)

## Scope
- Make regression scripts robust against docker project naming and tenancy mode.
- Ensure RBAC viewer tests are reliable against stale superuser flags.
- Ensure CAD attribute sync completes even when worker queue is behind.

## Changes
- verify_all: fallback docker compose port detection (no -p), export tenancy mode, and derive DB URL template/identity DB.
- verify_permissions: enforce viewer as non-superuser via admin API + membership upsert.
- verify_cad_sync: add direct cad_extract processor fallback when worker does not complete the job.

## Verification

Command:

```bash
bash scripts/verify_all.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
PASS: 18  FAIL: 0  SKIP: 0
ALL TESTS PASSED
```
