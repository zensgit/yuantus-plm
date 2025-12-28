# Day 8 - Audit Retention

## Scope
- Enable audit log retention controls and verify retention behavior.

## Changes
- Added audit retention settings and prune logic in audit middleware.
- Extended `scripts/verify_audit_logs.sh` to validate retention.
- Exposed retention envs in `docker-compose.yml` for API service.

## Verification

Command:

```bash
AUDIT_RETENTION_MAX_ROWS=5 AUDIT_RETENTION_DAYS=1 AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1 VERIFY_RETENTION=1 \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
  bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
Audit retention verified
ALL CHECKS PASSED
```
