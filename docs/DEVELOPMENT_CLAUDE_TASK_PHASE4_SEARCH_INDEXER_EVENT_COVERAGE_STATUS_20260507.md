# Development Task - Phase 4 P4.1.7 Search Indexer Event Coverage Status

Date: 2026-05-07

## 1. Goal

Make the incremental search indexer's event coverage explicit.

P4.1 through P4.1.6 exposed runtime health, counters, subscription status,
Prometheus metrics, and lag-age values. The remaining ambiguity is coverage:
the domain event catalog includes file/CAD events, but the search indexer only
has Elasticsearch indexing handlers for Item and ECO events. This slice exposes
that fact directly instead of silently implying full coverage.

## 2. Scope

- Add `indexed_event_types` to `GET /api/v1/search/indexer/status`.
- Add `unindexed_event_types`.
- Add `event_coverage`, mapping event type to `indexed` or `not_indexed`.
- Add Prometheus event coverage gauges.
- Add a drift contract that every concrete `DomainEvent` class is classified.
- Keep all previous P4.1 through P4.1.6 fields intact.
- Update tests, runtime runbook, TODO, DEV/verification MD, and delivery-doc
  index entries.

## 3. Non-Goals

- No file/CAD Elasticsearch indexing handler.
- No durable outbox table.
- No background indexing worker.
- No retry persistence.
- No document/BOM event model addition.
- No CAD material-sync plugin changes.

## 4. Public Surface

Existing admin endpoint:

```text
GET /api/v1/search/indexer/status
```

New additive JSON fields:

- `indexed_event_types`
- `unindexed_event_types`
- `event_coverage`

Existing metrics endpoint:

```text
GET /api/v1/metrics
```

New additive metric family:

- `yuantus_search_indexer_event_coverage{event_type="...",coverage="indexed|not_indexed"}`

## 5. Design

Current indexed events:

- `item.created`
- `item.updated`
- `item.state_changed`
- `item.deleted`
- `eco.created`
- `eco.updated`
- `eco.deleted`

Current unindexed events:

- `file.uploaded`
- `file.checked_in`
- `cad.attributes_synced`

The unindexed classification is intentional. `FileSearchService` currently
performs database-backed file search and does not provide an Elasticsearch
`index_file` equivalent. Adding fake handlers would create a false operational
signal. This slice records the current boundary honestly and adds a drift test
so future domain events must be classified.

## 6. Acceptance Criteria

- JSON status includes all three coverage fields.
- `indexed_event_types` matches the seven subscribed search index handlers.
- `unindexed_event_types` contains the file/CAD domain events.
- `event_coverage` accounts for every concrete `DomainEvent`.
- Prometheus emits one coverage gauge per classified event type.
- Route count remains unchanged.
- Existing health, lag-age, and outcome-counter tests remain green.

## 7. Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/yuantus/meta_engine/services/search_indexer.py \
  src/yuantus/meta_engine/web/search_router.py \
  src/yuantus/observability/metrics.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

## 8. Follow-Up

File/CAD incremental indexing should start only after a real file indexing
service contract exists. Durable Item/ECO indexing still requires a separate
outbox/job-backed taskbook.
