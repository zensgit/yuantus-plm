# C36 -- Document Sync Checkpoints / Retention Bootstrap -- Dev & Verification

## Status
- complete

## Branch
- Base: `feature/claude-greenfield-base-7`
- Branch: `feature/claude-c36-document-sync-checkpoints`

## Changed Files
1. `src/yuantus/meta_engine/document_sync/service.py` -- Added 4 service methods: `checkpoints_overview`, `retention_summary`, `site_checkpoints`, `export_retention`
2. `src/yuantus/meta_engine/web/document_sync_router.py` -- Added 4 router endpoints: `/checkpoints/overview`, `/retention/summary`, `/sites/{site_id}/checkpoints`, `/export/retention`
3. `src/yuantus/meta_engine/tests/test_document_sync_service.py` -- Added `TestCheckpointsRetention` class with 10 tests
4. `src/yuantus/meta_engine/tests/test_document_sync_router.py` -- Added 6 router tests for C36 endpoints
5. `docs/DESIGN_PARALLEL_C36_DOCUMENT_SYNC_CHECKPOINTS_RETENTION_BOOTSTRAP_20260320.md` -- Updated design doc
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C36_DOCUMENT_SYNC_CHECKPOINTS_RETENTION_BOOTSTRAP_20260320.md` -- This file

## Verification
1. `python3 -m pytest src/yuantus/meta_engine/tests/test_document_sync_service.py src/yuantus/meta_engine/tests/test_document_sync_router.py -v` -- 128 passed
2. `git diff --check` -- No whitespace errors

## Test Coverage (C36 additions)

### Service tests (TestCheckpointsRetention -- 10 tests)
- `test_checkpoints_overview` -- Mixed job states, completion rate, retention_ready=False
- `test_checkpoints_overview_empty` -- No data, None rate, retention_ready=False
- `test_retention_summary` -- Mixed outcomes with correct percentage calculations
- `test_retention_summary_no_records` -- No jobs, all None percentages
- `test_retention_summary_all_synced` -- 100% clean_sync_pct
- `test_site_checkpoints` -- Multiple jobs, checkpoint list, completion rate
- `test_site_checkpoints_no_jobs` -- Empty site, None rate, empty list
- `test_site_checkpoints_not_found` -- ValueError for missing site
- `test_export_retention` -- Combined payload structure verification
- `test_export_retention_empty` -- Empty combined payload

### Router tests (6 tests)
- `test_checkpoints_overview` -- 200 response with correct fields
- `test_retention_summary` -- 200 response with retention metrics
- `test_site_checkpoints` -- 200 response with per-site checkpoint data
- `test_site_checkpoints_not_found_404` -- 404 for ValueError
- `test_export_retention` -- 200 response with combined export payload
- `test_export_retention_empty` -- 200 response with empty structures

## Notes
- Router is NOT registered in `app.py` (greenfield constraint).
- All C36 methods follow established patterns from C21/C24/C27/C30/C33.
