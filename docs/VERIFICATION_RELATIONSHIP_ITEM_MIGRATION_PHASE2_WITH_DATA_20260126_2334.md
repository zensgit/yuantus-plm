# Relationship → Item Migration Phase 2 (With Legacy Data) Verification

## Data Setup
- Created three Part items via AML.
- Inserted two `meta_relationship_types` rows and three `meta_relationships` rows directly in Postgres.

## Dry-Run
```
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
python3 scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --dry-run --update-item-types
```
Log: `docs/VERIFY_REL_ITEM_MIGRATION_DRYRUN_WITH_DATA_20260126_2334.log`

## Apply
```
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus' \
YUANTUS_DATABASE_URL_TEMPLATE='postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id}' \
python3 scripts/migrate_relationship_items.py --tenant tenant-1 --org org-1 --update-item-types
```
Log: `docs/VERIFY_REL_ITEM_MIGRATION_APPLY_WITH_DATA_20260126_2334.log`

## Post-Check
```
select item_type_id, count(*)
from meta_items
where item_type_id like 'LegacyRelTest%'
 group by item_type_id;
```

Result:
- `LegacyRelTest-<ts>` → 2 rows
- `LegacyRelTestB-<ts>` → 1 row

## Status
`ALL CHECKS PASSED`

## Cleanup (optional)
To remove synthetic test data, delete the three items and the two relationship types from:
- `meta_items` (relationship items)
- `meta_relationships`
- `meta_relationship_types`
