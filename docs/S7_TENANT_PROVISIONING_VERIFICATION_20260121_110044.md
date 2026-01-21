# S7 Tenant Provisioning Verification (20260121_110044)

## Environment
- API: http://127.0.0.1:7910
- Tenancy: db-per-tenant-org
- Platform admin: enabled
- Identity DB: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg

## Command
```bash
MODE=db-per-tenant-org \
DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg' \
PLATFORM_TENANT=platform \
PLATFORM_ORG=platform \
PLATFORM_USER=platform-admin \
PLATFORM_PASSWORD=platform-admin \
PLATFORM_USER_ID=9001 \
  bash scripts/verify_tenant_provisioning.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Results
- Platform admin login: OK
- Platform admin access: OK
- Non-platform admin blocked: OK (403)
- Tenant created: tenant-provision-1768964444
- Tenant fetched: OK
- Extra org created: OK
- New tenant admin login: OK
- New tenant admin tenant info: OK

## Conclusion
Tenant provisioning via platform admin passes end-to-end.
