# Day 44 - Regression Validation (BOM/Where-Used/Version Files/CAD Connectors/MT/Audit)

## Scope
- Re-verify BOM Compare + Where-Used.
- Re-verify Version-File binding (checkout lock + checkin sync).
- Re-verify CAD connectors (2D/3D + config reload).
- Re-verify multi-tenancy isolation + audit logs.

## Verification

Commands:

```bash
export YUANTUS_TENANCY_MODE='db-per-tenant-org'
export YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export YUANTUS_IDENTITY_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_bom_compare.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_where_used.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_version_files.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_cad_connectors_2d.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_cad_connectors_3d.sh http://127.0.0.1:7910 tenant-1 org-1
bash scripts/verify_cad_connectors_config.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
export MODE='db-per-tenant-org'
export DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus'
export DB_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}'
export IDENTITY_DB_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg'

bash scripts/verify_multitenancy.sh http://127.0.0.1:7910 tenant-1 tenant-2 org-1 org-2
bash scripts/verify_audit_logs.sh http://127.0.0.1:7910 tenant-1 org-1
```

Result:

```text
ALL CHECKS PASSED
```
