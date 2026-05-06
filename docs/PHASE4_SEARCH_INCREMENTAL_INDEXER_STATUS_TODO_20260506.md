# TODO - Phase 4 P4.1 Search Incremental Indexer Status

Date: 2026-05-06

## Scope

- [x] Add runtime status counters for the existing search indexer.
- [x] Track registered handler names.
- [x] Track per-event receipt counts.
- [x] Track last received event.
- [x] Track last successful indexing handler.
- [x] Track last skipped handler when search is disabled.
- [x] Track last handler error.
- [x] Redact secret-like values from handler error status.
- [x] Add admin-only `/api/v1/search/indexer/status`.
- [x] Add focused unit and route tests.
- [x] Add taskbook and verification MD.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add a durable outbox table.
- [ ] Add a background indexing worker.
- [ ] Add retry persistence.
- [ ] Add file/document/BOM mutation indexing.
- [ ] Add search reports/RPC aggregation.
- [ ] Change search ranking or result shape.
- [ ] Require Elasticsearch in local tests.
