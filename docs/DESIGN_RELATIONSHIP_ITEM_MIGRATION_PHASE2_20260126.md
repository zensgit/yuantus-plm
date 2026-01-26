# Relationship → Item Migration Phase 2 Design (2026-01-26)

## Goal
Migrate legacy `meta_relationships` rows into `meta_items` (relationship-as-item) for db-per-tenant-org databases.

## Scope
- Create/align relationship `ItemType` metadata from `RelationshipType`.
- Migrate each relationship row into an `Item` row with:
  - `id = relationship.id`
  - `item_type_id = relationship_type.name (or id)`
  - `source_id`, `related_id`, `properties` (including `sort_order`)
  - `state` defaulting to `Active`
  - `permission_id` inherited from source item

## Tooling
- Script: `scripts/migrate_relationship_items.py`
- Mode: `db-per-tenant-org` (per-tenant/org databases)

## Execution Steps
1. Dry-run per tenant/org to detect missing types or missing source/related references.
2. Apply migration with `--update-item-types` to align relationship ItemType metadata.
3. Verify migrated count and log outputs.

## Notes
- In this environment, `meta_relationships` tables were empty for all tenant/org databases; migration safely no-oped.
- If missing types or missing source/related items are detected in other environments, rerun with `--allow-orphans` or fix data first.
