# Dev & Verification - Phase 4 Search Indexer Event Coverage Status

Date: 2026-05-07

## 1. Summary

Implemented P4.1.7: the search indexer now reports which domain events are
actually covered by incremental search indexing and which are not.

The result is explicit rather than aspirational: Item/ECO events are indexed;
file/CAD events are currently classified as `not_indexed` because there is no
file Elasticsearch indexing service equivalent to `SearchService.index_item` or
`SearchService.index_eco`.

## 2. Files Changed

- `src/yuantus/meta_engine/services/search_indexer.py`
- `src/yuantus/meta_engine/web/search_router.py`
- `src/yuantus/observability/metrics.py`
- `src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py`
- `src/yuantus/api/tests/test_observability_metrics_registry.py`
- `docs/RUNBOOK_RUNTIME.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE4_SEARCH_INDEXER_EVENT_COVERAGE_STATUS_20260507.md`
- `docs/PHASE4_SEARCH_INDEXER_EVENT_COVERAGE_STATUS_TODO_20260507.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_EVENT_COVERAGE_STATUS_20260507.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

New JSON fields on `GET /api/v1/search/indexer/status`:

- `indexed_event_types`
- `unindexed_event_types`
- `event_coverage`

New Prometheus family on `GET /api/v1/metrics`:

- `yuantus_search_indexer_event_coverage{event_type="...",coverage="indexed|not_indexed"}`

The drift contract introspects concrete `DomainEvent` classes and asserts that
`event_coverage` accounts for all of them. If a future PR adds a new domain
event, it must classify that event as indexed or not indexed.

## 4. Safety Boundaries

- No route-count change.
- No event handler behavior change.
- No existing status fields removed or renamed.
- No fake file/CAD indexing handler.
- No new high-cardinality metric labels.
- No durable outbox, worker, retry, replay, or Elasticsearch-required test.
- Primary CAD material-sync worktree was left untouched; this work ran in a
  temporary worktree.

## 5. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/services/search_indexer.py \
  src/yuantus/meta_engine/web/search_router.py \
  src/yuantus/observability/metrics.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

## 6. Verification Results

- `py_compile`: passed.
- Focused search/metrics tests: 26 passed.
- Focused P2/search/doc-index regression: 38 passed.
- Boot check: `routes=673 middleware=4`.
- `git diff --check`: clean.

## 7. Non-Goals

- No file/CAD Elasticsearch indexing.
- No document/BOM domain event model additions.
- No durable search outbox.
- No background indexing worker.
- No retry persistence.
- No CAD material-sync plugin changes.
