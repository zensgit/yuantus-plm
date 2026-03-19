# C30 -- Document Sync Drift / Snapshots Bootstrap -- Dev & Verification

## Status
- prepared

## Branch
- Base: `feature/claude-greenfield-base-5`
- Branch: `feature/claude-c30-document-sync-drift`

## Expected Changed Files
1. `src/yuantus/meta_engine/document_sync/service.py`
2. `src/yuantus/meta_engine/web/document_sync_router.py`
3. `src/yuantus/meta_engine/tests/test_document_sync_service.py`
4. `src/yuantus/meta_engine/tests/test_document_sync_router.py`
5. `docs/DESIGN_PARALLEL_C30_*`
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C30_*`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_document_sync_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Notes
- Keep all edits inside the isolated `document_sync` domain.
- Do not register the router in `app.py`.
