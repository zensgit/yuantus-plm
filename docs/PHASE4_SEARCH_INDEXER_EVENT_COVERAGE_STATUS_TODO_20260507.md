# TODO - Phase 4 P4.1.7 Search Indexer Event Coverage Status

Date: 2026-05-07

## Scope

- [x] Preserve all previous P4 search indexer status fields.
- [x] Add `indexed_event_types`.
- [x] Add `unindexed_event_types`.
- [x] Add `event_coverage`.
- [x] Classify Item/ECO events as `indexed`.
- [x] Classify file/CAD events as `not_indexed`.
- [x] Add DomainEvent drift contract.
- [x] Add Prometheus coverage gauge.
- [x] Update status endpoint response model.
- [x] Update metrics renderer tests.
- [x] Update runtime runbook.
- [x] Add taskbook and verification MD.
- [x] Update delivery-doc index.

## Explicitly Not Done

- [ ] Add file/CAD Elasticsearch indexing.
- [ ] Add document/BOM domain event models.
- [ ] Add durable search outbox.
- [ ] Add background search worker.
- [ ] Add retry persistence.
- [ ] Change CAD material-sync plugin files.
