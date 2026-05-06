# Dev & Verification - Phase 4 Search Indexer Subscription Status

Date: 2026-05-06

## 1. Summary

Implemented the P4.1.2 follow-up for search-indexer diagnostics: subscription
status.

P4.1 exposed the runtime status endpoint. P4.1.1 added per-event outcome
counters. This slice adds evidence that each expected event type is actually
subscribed to its expected in-process handler.

## 2. Files Changed

- `src/yuantus/meta_engine/services/search_indexer.py`
- `src/yuantus/meta_engine/web/search_router.py`
- `src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE4_SEARCH_INDEXER_SUBSCRIPTION_STATUS_20260506.md`
- `docs/PHASE4_SEARCH_INDEXER_SUBSCRIPTION_STATUS_TODO_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_SUBSCRIPTION_STATUS_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

`search_indexer.py` now uses one authoritative event-to-handler map for both:

- `register_search_index_handlers()`;
- `indexer_status()` subscription introspection.

New additive status fields:

- `subscription_counts`: exact expected-handler count by event type;
- `missing_handlers`: event types whose expected handler count is zero.

The subscription snapshot intentionally counts the exact expected handler
object, not merely any subscriber on the event type. That preserves signal even
if other listeners subscribe to the same event bus.

## 4. Safety Boundaries

- No existing status fields were removed or renamed.
- No durable outbox, worker, migration, or retry persistence was introduced.
- No event-bus persistence or public API redesign was introduced.
- Runtime indexing behavior is unchanged; only registration source-of-truth and
  diagnostics changed.
- This does not touch the CAD material-sync plugin worktree.

## 5. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  src/yuantus/meta_engine/services/search_indexer.py \
  src/yuantus/meta_engine/web/search_router.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/meta_engine/tests/test_search_service_fallback.py \
  src/yuantus/meta_engine/tests/test_admin_dependency_dedup.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -c \
  "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

## 6. Verification Results

- `py_compile`: passed.
- New search indexer status tests: 8 passed, 1 warning.
- Focused regression suite with doc-index trio: 21 passed, 1 warning.
- Boot check: `routes=673 middleware=4`.
- `git diff --check`: clean.

## 7. Non-Goals

- No durable outbox.
- No background worker.
- No retry persistence.
- No Elasticsearch dependency or test requirement.
- No search ranking changes.
- No P4 reports/RPC aggregation.
- No CAD material-sync plugin changes.
