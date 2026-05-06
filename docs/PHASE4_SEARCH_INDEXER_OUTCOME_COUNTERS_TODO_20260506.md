# TODO - Phase 4 P4.1.1 Search Indexer Outcome Counters

Date: 2026-05-06

## Scope

- [x] Preserve `event_counts` as received-event counts.
- [x] Add per-event `success_counts`.
- [x] Add per-event `skipped_counts`.
- [x] Add per-event `error_counts`.
- [x] Add `last_outcome`.
- [x] Increment success counts after handler completion.
- [x] Increment skipped counts when search is disabled.
- [x] Increment error counts when handler execution raises.
- [x] Preserve last-error redaction.
- [x] Extend admin endpoint response model.
- [x] Extend focused tests.
- [x] Add taskbook and verification MD.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add a durable outbox table.
- [ ] Add a background indexing worker.
- [ ] Add retry persistence.
- [ ] Add cross-process or cross-restart metrics.
- [ ] Add file/document/BOM mutation indexing.
- [ ] Change search ranking or result shape.
- [ ] Require Elasticsearch in local tests.
