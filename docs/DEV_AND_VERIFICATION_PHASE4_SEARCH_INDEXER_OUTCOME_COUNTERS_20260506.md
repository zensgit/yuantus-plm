# Dev & Verification - Phase 4 Search Indexer Outcome Counters

Date: 2026-05-06

## 1. Summary

Implemented the P4.1.1 follow-up for the search indexer status endpoint:
per-event outcome counters.

P4.1 made the existing event-driven search indexer observable at a basic
level. This follow-up keeps that endpoint additive and records whether each
event type is succeeding, being skipped because search is disabled, or failing.

## 2. Files Changed

- `src/yuantus/meta_engine/services/search_indexer.py`
- `src/yuantus/meta_engine/web/search_router.py`
- `src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE4_SEARCH_INDEXER_OUTCOME_COUNTERS_20260506.md`
- `docs/PHASE4_SEARCH_INDEXER_OUTCOME_COUNTERS_TODO_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_OUTCOME_COUNTERS_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The existing `event_counts` map remains the received-event counter.

New additive fields:

- `success_counts`
- `skipped_counts`
- `error_counts`
- `last_outcome`

Each count map uses the same seven event keys:

- `item.created`
- `item.updated`
- `item.state_changed`
- `item.deleted`
- `eco.created`
- `eco.updated`
- `eco.deleted`

Outcome recording happens in the shared `search_indexer._with_search_service`
wrapper, so all Item/ECO handlers follow the same accounting path.

## 4. Safety Boundaries

- No existing response field was removed or renamed.
- No outbox, worker, migration, or retry persistence was introduced.
- Search-disabled local/dev behavior remains a no-op, now with explicit
  `skipped_counts` accounting.
- Error diagnostics continue to use P4.1 redaction before being returned by the
  admin endpoint.
- The counters remain in-process diagnostics and reset on process restart.

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
- New search indexer status tests: 7 passed, 1 warning.
- Focused regression suite with doc-index trio: 20 passed, 1 warning.
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
