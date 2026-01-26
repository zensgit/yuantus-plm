# Relationship → Item Migration Phase 2 (With Legacy Data) Design (2026-01-26)

## Goal
Validate Phase 2 migration logic using real legacy rows in `meta_relationships`, ensuring they are copied into `meta_items` with correct linkage and properties.

## Why Direct SQL
Legacy relationship writes are blocked at the ORM layer (`meta_relationships` is deprecated for writes). We create a small synthetic dataset via SQL to exercise the migration path without changing app logic.

## Test Data
- Tenant/org DB: `yuantus_mt_pg__tenant-1__org-1`
- Parts created via AML: `LEG-REL-A-*`, `LEG-REL-B-*`, `LEG-REL-C-*`
- Relationship types:
  - `LegacyRelTest-<ts>`
  - `LegacyRelTestB-<ts>`
- Relationships (3 total):
  - A -> B (LegacyRelTest, quantity=2, sort_order=10)
  - B -> C (LegacyRelTest, quantity=3, sort_order=20)
  - A -> C (LegacyRelTestB, find_num=10, sort_order=30)

## Expected Migration
- 3 `meta_relationships` rows → 3 `meta_items` rows
- `item_type_id` matches relationship type id
- `properties` include `sort_order`
- `source_id` and `related_id` preserved

## Verification
- Run dry-run then apply with `scripts/migrate_relationship_items.py`
- Check counts in `meta_items` for `item_type_id` matching `LegacyRelTest%`
- Spot-check migrated rows for correct `source_id/related_id/properties`
