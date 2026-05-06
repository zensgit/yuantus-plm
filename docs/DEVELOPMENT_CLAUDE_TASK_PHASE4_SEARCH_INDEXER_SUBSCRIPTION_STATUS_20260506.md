# Development Task - Phase 4 P4.1.2 Search Indexer Subscription Status

Date: 2026-05-06

## 1. Goal

Continue Phase 4 search-indexer diagnostics without starting the durable
outbox/worker design.

P4.1 exposed the runtime status endpoint. P4.1.1 added per-event outcome
counters. The remaining low-risk diagnostic gap was subscription evidence:
`registered=true` indicated that registration code had run, but the status
payload did not prove that each expected event type had its expected handler
attached to the event bus.

## 2. Scope

- Add per-event `subscription_counts` to the existing indexer status payload.
- Add `missing_handlers` for expected handler subscriptions with count zero.
- Keep all prior P4.1/P4.1.1 fields intact.
- Refactor registration to use the same event-to-handler map used by the
  subscription snapshot.
- Extend focused tests for registration idempotence, expected handler
  presence, admin response shape, and existing outcome counters.
- Add this taskbook, TODO, DEV/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No outbox table.
- No background worker.
- No retry persistence.
- No event-bus persistence.
- No event-bus public API redesign.
- No search result ranking or response-shape changes.
- No CAD material-sync plugin changes.

## 4. Public Surface

Existing endpoint:

```text
GET /api/v1/search/indexer/status
```

New additive response fields:

- `subscription_counts`
- `missing_handlers`

Existing P4.1 and P4.1.1 fields remain present.

## 5. Design

`search_indexer.py` now has one authoritative event-to-handler map:

- `ItemCreatedEvent` -> `_handle_item_created`
- `ItemUpdatedEvent` -> `_handle_item_updated`
- `ItemStateChangedEvent` -> `_handle_item_state_changed`
- `ItemDeletedEvent` -> `_handle_item_deleted`
- `EcoCreatedEvent` -> `_handle_eco_created`
- `EcoUpdatedEvent` -> `_handle_eco_updated`
- `EcoDeletedEvent` -> `_handle_eco_deleted`

`register_search_index_handlers()` subscribes from this map. `indexer_status()`
uses the same map to count whether the exact expected handler object is present
for each event type in the in-memory event bus.

This intentionally remains diagnostic and in-process. It gives operators and
tests a cheap way to distinguish:

- registration code has not run;
- registration code ran but a handler is missing;
- registration and event outcomes are both visible.

## 6. Acceptance Criteria

- `subscription_counts` contains all seven event keys.
- `missing_handlers` is empty after registration.
- Each expected handler is subscribed exactly once after registration.
- Existing outcome counters remain present.
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

The durable outbox/job-backed indexer remains separate. It requires its own
taskbook because it changes persistence, retry behavior, ordering, and recovery
semantics.
