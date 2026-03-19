# C21 – Document Sync Analytics / Export Bootstrap – Dev & Verification

## Status
- planned_ready_for_claude

## Branch
- Base: `feature/claude-greenfield-base-2`
- Branch: `feature/claude-c21-document-sync-analytics`

## Scope
- `src/yuantus/meta_engine/document_sync/`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_*.py`

## Verification Required
1. `pytest src/yuantus/meta_engine/tests/test_document_sync_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`
