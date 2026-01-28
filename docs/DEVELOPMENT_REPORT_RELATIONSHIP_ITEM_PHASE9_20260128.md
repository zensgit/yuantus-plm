# Relationship Item Migration - Phase 9 (Internal References)

Date: 2026-01-28

## Goal

Remove internal runtime dependencies on `relationship.models` by switching
internal modules to import legacy models directly. This keeps the public
re-export path only for compatibility while internal code moves to the
explicit legacy module.

## Summary of Changes

- Admin routes now import legacy write-block helpers from
  `relationship.legacy_models`.
- Seeder now imports `RelationshipType` from `relationship.legacy_models`.
- Updated a misleading comment in `QueryService` to reflect that legacy
  RelationshipType fallback is removed.

## Files Changed

- `src/yuantus/api/routers/admin.py`
  - Import legacy write-block helpers from `legacy_models`.
- `src/yuantus/seeder/meta/schemas.py`
  - Import legacy `RelationshipType` from `legacy_models`.
- `src/yuantus/meta_engine/services/query_service.py`
  - Clarify relationship expansion comment.

## Risk

Low. Changes are import-only and documentation clarity; runtime behavior is
unchanged.

## Next

- Verify internal imports resolve to `legacy_models`.
- Record verification results.
