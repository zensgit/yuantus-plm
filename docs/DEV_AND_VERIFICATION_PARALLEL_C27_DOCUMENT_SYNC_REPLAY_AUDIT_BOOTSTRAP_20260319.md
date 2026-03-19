# C27 -- Document Sync Replay / Audit Bootstrap -- Dev & Verification

## Status
- complete

## Branch
- Base: `feature/claude-greenfield-base-4`
- Branch: `feature/claude-c27-document-sync-replay`

## Expected Changed Files
1. `src/yuantus/meta_engine/document_sync/service.py`
2. `src/yuantus/meta_engine/web/document_sync_router.py`
3. `src/yuantus/meta_engine/tests/test_document_sync_service.py`
4. `src/yuantus/meta_engine/tests/test_document_sync_router.py`
5. `docs/DESIGN_PARALLEL_C27_*`
6. `docs/DEV_AND_VERIFICATION_PARALLEL_C27_*`

## Verification
1. `pytest src/yuantus/meta_engine/tests/test_document_sync_*.py -v`
2. `bash scripts/check_allowed_paths.sh --mode staged`
3. `git diff --check`

## Test Results
```bash
pytest src/yuantus/meta_engine/tests/test_document_sync_*.py -v
80 passed
```

## Codex Integration Verification
- candidate stack branch: `feature/codex-c26c27-staging`
- cherry-pick source: `608d4cd`
- integrated commit: `f828406`
- combined regression with `C26`:
  - `140 passed, 55 warnings in 2.35s`
- unified stack script on staging:
  - `425 passed, 151 warnings in 13.34s`
- `git diff --check`: passed

## Notes
- Keep all edits inside the isolated `document_sync` domain.
- Do not register the router in `app.py`.
