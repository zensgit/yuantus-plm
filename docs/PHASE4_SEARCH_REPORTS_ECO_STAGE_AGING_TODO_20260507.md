# TODO - Phase 4 P4.2.2 Search Reports ECO Stage Aging

Date: 2026-05-07

## Scope

- [x] Keep P4.2.1 summary response shape unchanged.
- [x] Add DB-backed `SearchService.eco_stage_aging_report()`.
- [x] Group ECOs by `stage_id`.
- [x] Normalize null and blank stage IDs to `unknown`.
- [x] Use `updated_at` as the first age timestamp.
- [x] Fall back to `created_at`.
- [x] Treat missing timestamps as `0.0` days.
- [x] Add admin route `GET /api/v1/search/reports/eco-stage-aging`.
- [x] Return JSON by default.
- [x] Return CSV when `format=csv`.
- [x] Add route ownership and authorization tests.
- [x] Update app route-count guard to `675`.
- [x] Add design and verification markdown.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add ECO stage transition history.
- [ ] Add SLA thresholds.
- [ ] Add alerts or metrics.
- [ ] Add Elasticsearch aggregation queries.
- [ ] Add saved report persistence.
- [ ] Add dashboard UI.
- [ ] Change CAD material-sync plugin files.
