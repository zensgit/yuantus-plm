# Development Report - Relationship Item Phase 6 (Legacy Runtime Removal)

Date: 2026-01-28

## Goal
Remove runtime dependency on legacy `RelationshipType` for relationship resolution
while keeping migration/statistics tooling available.

## Changes Delivered
- `RelationshipService` now resolves relationships **only** via `ItemType.is_relationship`.
- AML query `expand` no longer falls back to legacy `RelationshipType`.
- Legacy relationship types remain available only for migration/usage reporting.

## Files Touched
- `src/yuantus/meta_engine/relationship/service.py`
- `src/yuantus/meta_engine/services/query_service.py`
- `docs/DEVELOPMENT_REPORT_RELATIONSHIP_ITEM_PHASE6_20260128.md`
