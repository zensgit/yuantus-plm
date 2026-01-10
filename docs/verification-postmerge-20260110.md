# Post-merge Verification Report (2026-01-10)

## Environment
- Base URL: http://127.0.0.1:7910
- Tenancy mode: single
- Database: sqlite:///./yuantus_dev.db
- Auth: required

## CAD 2D Preview + Metadata
- Command:
  - `CAD_PREVIEW_ALLOW_FALLBACK=1 YUANTUS_DATABASE_URL=sqlite:///./yuantus_dev.db YUANTUS_TENANCY_MODE=single bash scripts/verify_cad_preview_2d.sh http://127.0.0.1:7910 tenant-1 org-1`
- Result: ALL CHECKS PASSED
- Notes:
  - CAD ML Vision unavailable → fallback preview used.
  - Mesh stats endpoint returned 404 (optional; script skips).

## Search Reindex
- Command:
  - `YUANTUS_DATABASE_URL=sqlite:///./yuantus_dev.db YUANTUS_TENANCY_MODE=single bash scripts/verify_search_reindex.sh http://127.0.0.1:7910 tenant-1 org-1`
- Result: ALL CHECKS PASSED
- Engine: db
