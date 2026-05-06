# Development Task - Phase 4 P4.1.3 Search Indexer Lifecycle Status

Date: 2026-05-06

## 1. Goal

Continue Phase 4 search-indexer diagnostics with an additive lifecycle-status
slice.

P4.1 exposed runtime counters. P4.1.1 added outcome counters. P4.1.2 added
subscription evidence. The remaining low-risk diagnostic gap was lifecycle
context: a zero counter could mean no events arrived, or it could mean the
process just restarted and reset the in-process counters.

## 2. Scope

- Add `status_started_at` to the existing indexer status payload.
- Add `uptime_seconds`.
- Add `registered_at` when search-index handlers are first registered.
- Keep all prior P4.1/P4.1.1/P4.1.2 fields intact.
- Extend focused tests for lifecycle fields and registration timestamp.
- Add this taskbook, TODO, DEV/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No durable outbox table.
- No background indexing worker.
- No retry persistence.
- No cross-process metrics.
- No event-bus persistence or public API redesign.
- No search ranking or result-shape changes.
- No CAD material-sync plugin changes.

## 4. Public Surface

Existing endpoint:

```text
GET /api/v1/search/indexer/status
```

New additive response fields:

- `status_started_at`
- `uptime_seconds`
- `registered_at`

Existing P4.1, P4.1.1, and P4.1.2 fields remain present.

## 5. Design

`status_started_at` is captured when the `search_indexer` module initializes
its in-process diagnostic state. `uptime_seconds` is derived from that timestamp
when `indexer_status()` is called.

`registered_at` is set when `register_search_index_handlers()` successfully
subscribes the expected handlers for the first time. It remains `null` before
registration.

These fields are process-local diagnostics. They do not claim durable uptime or
cluster-wide uptime. Their purpose is to help operators interpret in-process
counters after deploys, restarts, or test app construction.

## 6. Acceptance Criteria

- `status_started_at` is always present and UTC-formatted.
- `uptime_seconds` is always present and non-negative.
- `registered_at` is set after handler registration.
- Existing counters and subscription fields remain present.
- Admin endpoint returns the additive fields.
- Non-admin behavior remains 403.
- Boot route count remains stable.

## 7. Verification Plan

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

## 8. Follow-Up

Durable indexing, replay, and retry remain separate. Those changes need a new
taskbook because they change persistence and recovery semantics.
