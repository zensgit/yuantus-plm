# Development Report - Relationship Item Phase 7 (Legacy Runtime Detach)

Date: 2026-01-28

## Goal
Detach runtime admin reporting from ORM legacy models so the core runtime
no longer imports legacy `Relationship`/`RelationshipType` classes.

## Changes Delivered
- Admin legacy usage report now uses raw SQL against legacy tables instead of
  ORM models, removing runtime model imports.
- Core runtime keeps migration/compat tooling while avoiding ORM coupling.

## Files Touched
- `src/yuantus/api/routers/admin.py`
- `docs/DEVELOPMENT_REPORT_RELATIONSHIP_ITEM_PHASE7_20260128.md`
