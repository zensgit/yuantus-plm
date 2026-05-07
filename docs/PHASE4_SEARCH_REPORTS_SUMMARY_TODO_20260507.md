# TODO - Phase 4 P4.2.1 Search Reports Summary

Date: 2026-05-07

## Scope

- [x] Keep P4.1 search indexer behavior unchanged.
- [x] Add DB-backed `SearchService.reports_summary()`.
- [x] Aggregate items by `item_type_id`.
- [x] Aggregate items by `state`.
- [x] Aggregate ECOs by `state`.
- [x] Aggregate ECOs by `stage_id`.
- [x] Normalize null and blank bucket keys to `unknown`.
- [x] Add admin route `GET /api/v1/search/reports/summary`.
- [x] Return JSON by default.
- [x] Return CSV when `format=csv`.
- [x] Add route ownership and authorization tests.
- [x] Update app route-count guard to `674`.
- [x] Add design and verification markdown.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add Elasticsearch aggregation queries.
- [ ] Add saved report persistence.
- [ ] Add scheduled report execution.
- [ ] Add dashboard UI.
- [ ] Add file/CAD report buckets.
- [ ] Change search indexer event handlers.
- [ ] Change CAD material-sync plugin files.
