# S7 Deep Verification Design (2026-01-25)

## Goal
Validate multi-tenant isolation and ops hardening in db-per-tenant-org mode.

## Scope
- Multi-tenancy isolation (tenant + org)
- Quotas
- Audit logs
- Ops health
- Search reindex
- Tenant provisioning (platform admin)

## Key Checks
1. **Isolation**: items created in tenant/org do not appear across other tenant/org scopes.
2. **Quotas**: org/user/file/job quotas enforce limits.
3. **Audit**: health and CRUD actions produce logs.
4. **Ops**: /health and /health/deps are healthy.
5. **Search**: reindex runs and search results reflect updates.
6. **Provisioning**: platform admin can create tenant/org + default admin; non-platform admin is blocked.

## Environment
- API: `http://127.0.0.1:7910`
- Tenancy mode: `db-per-tenant-org`
- Postgres:
  - `YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus`
  - `YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}`
  - `YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg`

## Script
- `scripts/verify_s7.sh`
