# Relationship-as-Item Verification (2026-01-23 13:07 +0800)

Goal: Validate BOM/ECO/Version flows after unifying relationships to `meta_items`.

## Environment

- Base URL: http://127.0.0.1:7910
- Tenancy: db-per-tenant-org
- DB:
  - DATABASE_URL: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus
  - DATABASE_URL_TEMPLATE: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}
  - IDENTITY_DATABASE_URL: postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg

## Commands

```bash
bash scripts/verify_bom_tree.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
MODE=db-per-tenant-org \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
DB_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_bom_effectivity.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
bash scripts/verify_versions.sh http://127.0.0.1:7910 tenant-1 org-1
```

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
IDENTITY_DB_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  bash scripts/verify_eco_advanced.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Result

```text
verify_bom_tree: ALL CHECKS PASSED
verify_bom_effectivity: ALL CHECKS PASSED
verify_versions: ALL CHECKS PASSED
verify_eco_advanced: ALL CHECKS PASSED
```
