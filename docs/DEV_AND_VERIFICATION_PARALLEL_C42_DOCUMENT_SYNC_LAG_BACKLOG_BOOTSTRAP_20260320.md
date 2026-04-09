# C42 Dev & Verification: Document Sync Lag / Backlog Bootstrap

## Planned Changed Files
- `src/yuantus/meta_engine/document_sync/service.py` - 4 new methods (C42 section)
- `src/yuantus/meta_engine/web/document_sync_router.py` - 4 new endpoints (C42 section)
- `src/yuantus/meta_engine/tests/test_document_sync_service.py` - C42 test class
- `src/yuantus/meta_engine/tests/test_document_sync_router.py` - C42 endpoint tests

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_document_sync_*.py -v
bash scripts/check_allowed_paths.sh --mode staged
git diff --check
```

## Planned Coverage
- lag_overview: with data, empty, delayed-job distribution
- backlog_summary: with data, empty
- site_backlog: with jobs, empty site, not found
- export_backlog: with data, empty
- Router: all 4 endpoints + 404 case

## Codex Integration Target
- candidate stack branch: `feature/codex-c41c42-staging`
- Claude branch baseline: `feature/claude-greenfield-base-9`
