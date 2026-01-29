# Relationship-as-Item Unification Design (2026-01-29)

## Goal
Confirm the system uses **ItemType.is_relationship + Item rows** as the single write path for relationships, while keeping legacy `meta_relationships` / `RelationshipType` as **read-only compatibility**.

## Current Architecture (Confirmed)
- **Write path**: `meta_items` only (relationship rows are `Item` with `item_type_id` = relationship ItemType).
- **Schema source**: `ItemType.is_relationship=true` (e.g., `Part BOM`).
- **Legacy**: `meta_relationships` and `RelationshipType` are **deprecated**, read-only, and guarded.

## Verified Components
- `RelationshipService` resolves relationship type **only** via `ItemType.is_relationship`.
- `BOMService` creates/queries BOM relationships as `Item` rows (`Part BOM`).
- `ECOBOMChange.relationship_item_id` targets **`meta_items.id`**, matching relationship-as-item semantics.
- Legacy seeding of `RelationshipType` is **optional**, gated by `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED=true`.

## Data Compatibility
- Legacy relationship data can be migrated into `meta_items` using the existing migration script/runbook.
- `meta_relationships` stays in place for legacy read/metrics, but writes are blocked.

## Verification
- `scripts/verify_relationship_itemtype_expand.sh`
- `scripts/verify_relationship_type_seeding.sh`

## Notes
- No code changes required for unification at this stage; the runtime already uses Item-only relationships.
- Migration is a data task (optional), documented in `docs/RUNBOOK_RELATIONSHIP_ITEM_MIGRATION.md`.
