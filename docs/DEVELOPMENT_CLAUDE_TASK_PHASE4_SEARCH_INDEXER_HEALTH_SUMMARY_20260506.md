# Development Task - Phase 4 P4.1.4 Search Indexer Health Summary

Date: 2026-05-06

## 1. Goal

Continue Phase 4 search-indexer diagnostics with a small, additive health
summary.

P4.1 through P4.1.3 exposed registration, counters, outcome counts,
subscription status, and lifecycle context. The status payload was detailed but
still required clients to infer whether the indexer was healthy from several
fields. This slice adds a machine-readable summary without changing runtime
indexing behavior.

## 2. Scope

- Add `health` to the existing indexer status payload.
- Add `health_reasons`.
- Add `duplicate_handlers`.
- Keep all prior P4.1/P4.1.1/P4.1.2/P4.1.3 fields intact.
- Extend focused tests for healthy, missing-handler, duplicate-handler, and
  not-registered status.
- Add this taskbook, TODO, DEV/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No durable outbox table.
- No background indexing worker.
- No retry persistence.
- No cross-process health aggregation.
- No event-bus persistence or public API redesign.
- No search ranking or result-shape changes.
- No CAD material-sync plugin changes.

## 4. Public Surface

Existing endpoint:

```text
GET /api/v1/search/indexer/status
```

New additive response fields:

- `health`
- `health_reasons`
- `duplicate_handlers`

Existing P4.1, P4.1.1, P4.1.2, and P4.1.3 fields remain present.

## 5. Design

`health` is derived from registration and subscription state:

- `ok`: registered and every expected handler is subscribed exactly once.
- `not_registered`: registration has not run and no other anomaly is present.
- `degraded`: one or more anomaly reasons are present.

`health_reasons` uses stable string values:

- `not-registered`
- `missing-handlers`
- `duplicate-handlers`

`duplicate_handlers` lists expected event types whose exact expected handler is
subscribed more than once. This complements `missing_handlers`, which lists
expected event types whose exact expected handler is missing.

## 6. Acceptance Criteria

- Healthy registered state reports `health=ok`.
- Missing handler subscriptions report `degraded` and `missing-handlers`.
- Duplicate handler subscriptions report `degraded` and `duplicate-handlers`.
- Not-registered state reports `not-registered` in `health_reasons`.
- Existing counters, lifecycle fields, and subscription counts remain present.
- Admin endpoint returns the additive fields.
- Non-admin behavior remains 403.

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

Durable outbox, retry, replay, and worker scheduling remain separate and should
start from a dedicated taskbook because they alter persistence and recovery
semantics.
