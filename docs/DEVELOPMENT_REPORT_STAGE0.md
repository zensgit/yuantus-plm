# Stage 0 Development Report - CI and Verification Hardening

Date: 2026-01-09

## Goal
Stabilize the CADGF preview verification path in CI and document the required
runtime environment.

## Changes Delivered
- Documented CADGF preview verification environment variables, including the
  CI-only fallback toggle (`CADGF_SYNC_GEOMETRY`).
- Confirmed the split `cadgf_preview` job design is live on `main` (merged
  in PR #17).

## Files Touched
- `docs/CADGF_PREVIEW_ENV.md`

## Notes
- The `cadgf_preview` job remains the authoritative CI gate for CADGF preview
  metadata generation; the main regression job stays lean.
