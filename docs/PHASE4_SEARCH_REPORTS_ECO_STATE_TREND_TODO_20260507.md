# TODO - Phase 4 P4.2.3 Search Reports ECO State Trend

Date: 2026-05-07

## Scope

- [x] Keep P4.2.1 summary response shape unchanged.
- [x] Keep P4.2.2 stage aging response shape unchanged.
- [x] Add DB-backed `SearchService.eco_state_trend_report()`.
- [x] Group ECOs by UTC `created_at` date.
- [x] Group ECOs by current `state`.
- [x] Normalize null and blank state to `unknown`.
- [x] Add `days` query parameter.
- [x] Enforce `days` bounds `1..366`.
- [x] Add admin route `GET /api/v1/search/reports/eco-state-trend`.
- [x] Return JSON by default.
- [x] Return CSV when `format=csv`.
- [x] Add route ownership and authorization tests.
- [x] Update app route-count guard to `676`.
- [x] Add design and verification markdown.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add ECO state transition history.
- [ ] Reconstruct lifecycle events from audit logs.
- [ ] Add SLA thresholds.
- [ ] Add alerts or metrics.
- [ ] Add Elasticsearch aggregation queries.
- [ ] Add saved report persistence.
- [ ] Add dashboard UI.
- [ ] Change CAD material-sync plugin files.
