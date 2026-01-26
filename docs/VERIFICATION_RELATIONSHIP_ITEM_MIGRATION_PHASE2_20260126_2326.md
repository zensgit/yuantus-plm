# Relationship → Item Migration Phase 2 Verification (2026-01-26 23:26 +0800)

## Dry-Run
```
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
python3 scripts/migrate_relationship_items.py --tenant <tenant> --org <org> --dry-run --update-item-types
```

Log: `docs/VERIFY_REL_ITEM_MIGRATION_DRYRUN_20260126_2325.log`

## Apply
```
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
python3 scripts/migrate_relationship_items.py --tenant <tenant> --org <org> --update-item-types
```

Log: `docs/VERIFY_REL_ITEM_MIGRATION_APPLY_20260126_2326.log`

## Result
- Tenant/org DBs processed: tenant-1/org-1, tenant-1/org-2, tenant-2/org-1, tenant-2/org-2
- Relationships found: `0` in each DB
- Migrated items: `0`
- Status: `ALL CHECKS PASSED`
