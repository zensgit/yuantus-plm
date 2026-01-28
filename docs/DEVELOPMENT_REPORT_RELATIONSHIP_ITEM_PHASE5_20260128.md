# Development Report - Relationship Item Phase 5 (Legacy Gate)

Date: 2026-01-28

## Goal
Gate legacy `RelationshipType` usage behind explicit configuration so runtime
relationships only resolve via `ItemType.is_relationship` by default.

## Changes Delivered
- `RelationshipService._resolve_relationship_type` now requires an ItemType
  unless `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED=true`.
- AML query `expand` ignores `RelationshipType` fallback unless legacy mode is enabled.
- Legacy usage retains warnings/logs but no longer influences runtime behavior by default.

## Files Touched
- `src/yuantus/meta_engine/relationship/service.py`
- `src/yuantus/meta_engine/services/query_service.py`
- `docs/DEVELOPMENT_REPORT_RELATIONSHIP_ITEM_PHASE5_20260128.md`
