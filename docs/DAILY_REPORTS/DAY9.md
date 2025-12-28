# Day 9 - Ops Health Endpoint

## Scope
- Add dependency health endpoint and verification script.

## Changes
- Added `/api/v1/health/deps` with DB/identity/storage checks.
- Allowed `/api/v1/health/deps` as public path in auth middleware.
- Added `scripts/verify_ops_health.sh` and included it in `verify_all.sh`.

## Verification

Command:

```bash
bash scripts/verify_ops_health.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
Health deps: OK
ALL CHECKS PASSED
```
