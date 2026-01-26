# S7 Deep Verification (2026-01-25 23:02 +0800)

## Command
```
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
RUN_TENANT_PROVISIONING=1 \
bash scripts/verify_s7.sh http://127.0.0.1:7910 tenant-1 org-1 tenant-2 org-2 \
  | tee docs/VERIFY_S7_20260125_2302.log
```

## Result Summary
- Multi-tenancy: PASS
- Quotas: PASS
- Audit logs: PASS
- Ops health: PASS
- Search reindex: PASS
- Tenant provisioning: PASS

## Output
`ALL CHECKS PASSED`
