# TODO - Phase 4 P4.1.3 Search Indexer Lifecycle Status

Date: 2026-05-06

## Scope

- [x] Preserve P4.1 status fields.
- [x] Preserve P4.1.1 outcome counters.
- [x] Preserve P4.1.2 subscription status.
- [x] Add `status_started_at`.
- [x] Add `uptime_seconds`.
- [x] Add `registered_at`.
- [x] Cover lifecycle fields in focused tests.
- [x] Cover registration timestamp after handler registration.
- [x] Add taskbook and verification MD.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add a durable outbox table.
- [ ] Add a background indexing worker.
- [ ] Add retry persistence.
- [ ] Add cross-process metrics.
- [ ] Add cluster-wide uptime semantics.
- [ ] Add file/document/BOM mutation indexing.
- [ ] Require Elasticsearch in local tests.
