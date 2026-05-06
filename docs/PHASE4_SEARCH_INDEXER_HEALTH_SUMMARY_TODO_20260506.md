# TODO - Phase 4 P4.1.4 Search Indexer Health Summary

Date: 2026-05-06

## Scope

- [x] Preserve P4.1 status fields.
- [x] Preserve P4.1.1 outcome counters.
- [x] Preserve P4.1.2 subscription status.
- [x] Preserve P4.1.3 lifecycle fields.
- [x] Add `health`.
- [x] Add `health_reasons`.
- [x] Add `duplicate_handlers`.
- [x] Cover healthy registered state.
- [x] Cover missing-handler and duplicate-handler anomalies.
- [x] Cover not-registered health reason.
- [x] Add taskbook and verification MD.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add a durable outbox table.
- [ ] Add a background indexing worker.
- [ ] Add retry persistence.
- [ ] Add cross-process health aggregation.
- [ ] Redesign the event bus public API.
- [ ] Add file/document/BOM mutation indexing.
- [ ] Require Elasticsearch in local tests.
