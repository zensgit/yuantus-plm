# S8 Ops Monitoring Verification

## Preconditions
- `YUANTUS_QUOTA_MODE=enforce`
- `YUANTUS_AUDIT_ENABLED=true`
- `YUANTUS_PLATFORM_ADMIN_ENABLED=true`

Optional retention configuration (to exercise pruning):
- `YUANTUS_AUDIT_RETENTION_DAYS=1`
- `YUANTUS_AUDIT_RETENTION_MAX_ROWS=10`
- `YUANTUS_AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS=1`

If retention-days validation is needed, set:
- `YUANTUS_IDENTITY_DATABASE_URL` or `IDENTITY_DB_URL`

## One-Click Validation

```bash
bash scripts/verify_ops_s8.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Manual Checks

### 1) Quota Monitoring

```bash
curl -s http://127.0.0.1:7910/api/v1/admin/tenants/quotas \
  -H "Authorization: Bearer <platform_token>" \
  -H "x-tenant-id: platform"
```

Expect `items[]` list with `tenant_id`, `quota`, and `usage` fields.

### 2) Audit Retention

```bash
curl -s http://127.0.0.1:7910/api/v1/admin/audit/retention \
  -H "Authorization: Bearer <admin_token>" \
  -H "x-tenant-id: tenant-1" -H "x-org-id: org-1"

curl -s -X POST http://127.0.0.1:7910/api/v1/admin/audit/prune \
  -H "Authorization: Bearer <admin_token>" \
  -H "x-tenant-id: tenant-1" -H "x-org-id: org-1"
```

Expect retention settings and a `deleted` count.

### 3) Reports Summary Meta

```bash
curl -s http://127.0.0.1:7910/api/v1/reports/summary \
  -H "Authorization: Bearer <admin_token>" \
  -H "x-tenant-id: tenant-1" -H "x-org-id: org-1"
```

Expect `meta` with `tenant_id`, `org_id`, `tenancy_mode`, and `generated_at`.
