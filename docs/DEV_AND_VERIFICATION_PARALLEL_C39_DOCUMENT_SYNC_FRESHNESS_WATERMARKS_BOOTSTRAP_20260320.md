# C39 — Document Sync Freshness / Watermarks Bootstrap — Dev & Verification

## Implementation Summary

- **Service**: 4 new methods in `DocumentSyncService` (freshness_overview, watermarks_summary, site_freshness, export_watermarks)
- **Router**: 4 new endpoints in `document_sync_router` under C39 section
- **Tests**: 11 service tests in `TestFreshnessWatermarks` class + 7 router tests

## Files Changed

| File | Change |
|---|---|
| `src/yuantus/meta_engine/document_sync/service.py` | Added C39 freshness/watermarks section (4 methods) |
| `src/yuantus/meta_engine/web/document_sync_router.py` | Added C39 endpoint section (4 endpoints) |
| `src/yuantus/meta_engine/tests/test_document_sync_service.py` | Added `TestFreshnessWatermarks` class (11 tests) |
| `src/yuantus/meta_engine/tests/test_document_sync_router.py` | Added C39 router tests (7 tests) |

## Test Coverage

### Service Tests (TestFreshnessWatermarks)
- `test_freshness_overview` — mixed sync outcomes, correct avg/freshest/stalest
- `test_freshness_overview_empty` — no data, None values
- `test_freshness_overview_all_fresh` — 100% freshness, zero stale
- `test_watermarks_summary` — sites with varying freshness, threshold check
- `test_watermarks_summary_empty` — no sites
- `test_watermarks_summary_exceeded` — site below threshold flagged
- `test_site_freshness` — per-site detail with stale docs
- `test_site_freshness_no_jobs` — site exists, no jobs
- `test_site_freshness_not_found` — ValueError on missing site
- `test_export_watermarks` — combined export payload
- `test_export_watermarks_empty` — empty export

### Router Tests
- `test_freshness_overview` — GET /freshness/overview
- `test_watermarks_summary` — GET /watermarks/summary
- `test_site_freshness` — GET /sites/{site_id}/freshness
- `test_site_freshness_not_found_404` — 404 on missing site
- `test_export_watermarks` — GET /export/watermarks
- `test_export_watermarks_empty` — empty export response

## Verification

```bash
python3 -m pytest src/yuantus/meta_engine/tests/test_document_sync_service.py src/yuantus/meta_engine/tests/test_document_sync_router.py -v
# 145 passed
```
