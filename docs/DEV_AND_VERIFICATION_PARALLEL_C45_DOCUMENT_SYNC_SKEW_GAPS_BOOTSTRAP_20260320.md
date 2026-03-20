# C45 Dev & Verification: Document Sync Skew / Gaps Bootstrap

## Planned Changed Files
- `src/yuantus/meta_engine/document_sync/service.py` - 4 new methods (C45 section)
- `src/yuantus/meta_engine/web/document_sync_router.py` - 4 new endpoints (C45 section)
- `src/yuantus/meta_engine/tests/test_document_sync_service.py` - C45 test class
- `src/yuantus/meta_engine/tests/test_document_sync_router.py` - C45 endpoint tests

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_document_sync_*.py -v
bash scripts/check_allowed_paths.sh --mode staged
git diff --check
```

## Planned Coverage
- skew_overview: with data, empty, severity distribution
- gaps_summary: with data, empty
- site_gaps: with jobs, empty site, not found
- export_gaps: with data, empty
- Router: all 4 endpoints + 404 case

## Codex Integration Target
- candidate stack branch: `feature/codex-c44c45-staging`
- Claude branch baseline: `feature/claude-greenfield-base-10`
