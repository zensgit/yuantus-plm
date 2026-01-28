# Relationship Item Migration - Phase 10 (Deprecated Guard + Import Check)

Date: 2026-01-28

## Goal

Add explicit deprecation warnings for legacy relationship imports and provide a
simple internal guard script to prevent new usage inside the codebase.

## Summary of Changes

- Added a `DeprecationWarning` on import of `relationship.models`.
- Added `scripts/check_no_legacy_relationship_imports.sh` to enforce that
  internal code does not import `relationship.models`.

## Files Changed

- `src/yuantus/meta_engine/relationship/models.py`
  - Emits a `DeprecationWarning` on import.
- `scripts/check_no_legacy_relationship_imports.sh`
  - New guard script (scans `src` for forbidden imports).

## Risk

Low. Warning is non-fatal; guard script is opt-in for verification.

## Next

- Record verification run in results.
