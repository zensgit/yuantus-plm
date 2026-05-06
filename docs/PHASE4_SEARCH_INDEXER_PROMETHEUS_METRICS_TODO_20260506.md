# TODO - Phase 4 P4.1.5 Search Indexer Prometheus Metrics

Date: 2026-05-06

## Scope

- [x] Preserve `GET /api/v1/search/indexer/status`.
- [x] Preserve Phase 2 job metric registry rendering.
- [x] Add runtime metrics renderer for `/api/v1/metrics`.
- [x] Emit search indexer registration gauge.
- [x] Emit search indexer uptime gauge.
- [x] Emit health-state gauges.
- [x] Emit active health-reason gauges.
- [x] Emit item/ECO index-ready gauges.
- [x] Emit event subscription gauges.
- [x] Emit received/success/skipped/error event counters.
- [x] Keep last error text out of metrics.
- [x] Update endpoint tests for the non-empty runtime metrics surface.
- [x] Update runtime runbook.
- [x] Add development and verification MD.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add a durable outbox table.
- [ ] Add a background indexing worker.
- [ ] Add retry persistence.
- [ ] Add cross-process aggregation.
- [ ] Add an admin metric reset endpoint.
- [ ] Add tenant/org/user/item/ECO labels.
- [ ] Change CAD material-sync plugin files.
