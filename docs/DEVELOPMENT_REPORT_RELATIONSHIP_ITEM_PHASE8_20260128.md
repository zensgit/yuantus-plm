# Relationship Item Migration - Phase 8 (Soft Migration)

Date: 2026-01-28

## Goal

Move legacy Relationship ORM definitions to a dedicated module while keeping the
public import path stable. This reduces coupling to deprecated models without
breaking existing imports.

## Summary of Changes

- Added `legacy_models.py` to host deprecated Relationship ORM models.
- Converted `models.py` into a thin re-export wrapper so existing imports remain
  valid (no runtime behavior change).
- Kept write-block protections on legacy tables intact.

## Files Changed

- `src/yuantus/meta_engine/relationship/legacy_models.py`
  - New location of `Relationship` / `RelationshipType` and write-block helpers.
- `src/yuantus/meta_engine/relationship/models.py`
  - Re-exports from `legacy_models` and documents deprecation intent.

## Why This Approach

- Preserves import compatibility for any existing code or integrations.
- Keeps deprecated models isolated, making future removal safer.
- Maintains write protection to prevent new usage of `meta_relationships`.

## Risks

- Low risk. Import path compatibility is preserved and behavior is unchanged.
- If any code relies on module-level side effects from the old file, those are
  still present because the legacy module is imported by the wrapper.

## Next

- Verify import compatibility and write-block behavior.
- Update verification logs and results summary.
