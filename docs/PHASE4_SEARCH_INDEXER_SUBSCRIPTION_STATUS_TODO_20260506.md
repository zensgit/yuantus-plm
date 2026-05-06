# TODO - Phase 4 P4.1.2 Search Indexer Subscription Status

Date: 2026-05-06

## Scope

- [x] Preserve P4.1 status fields.
- [x] Preserve P4.1.1 outcome counters.
- [x] Add per-event `subscription_counts`.
- [x] Add `missing_handlers`.
- [x] Use one event-to-handler map for registration and subscription snapshots.
- [x] Cover expected registration after `register_search_index_handlers()`.
- [x] Cover admin endpoint response shape.
- [x] Add taskbook and verification MD.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add a durable outbox table.
- [ ] Add a background indexing worker.
- [ ] Add retry persistence.
- [ ] Add cross-process subscription inspection.
- [ ] Redesign the event bus public API.
- [ ] Add file/document/BOM mutation indexing.
- [ ] Require Elasticsearch in local tests.
