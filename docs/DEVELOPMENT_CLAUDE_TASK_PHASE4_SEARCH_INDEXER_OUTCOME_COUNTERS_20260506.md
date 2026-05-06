# Development Task - Phase 4 P4.1.1 Search Indexer Outcome Counters

Date: 2026-05-06

## 1. Goal

Continue Phase 4 search-indexing work with the smallest safe follow-up after
P4.1.

P4.1 exposed whether the in-process incremental indexer was registered and
whether it had received events. The remaining diagnostic gap was outcome
distribution: operators could see the last success, skip, or error, but not
whether a specific event type was repeatedly succeeding, being skipped because
search was disabled, or failing.

## 2. Scope

- Keep the existing `event_counts` field as the received-event counter.
- Add per-event `success_counts`.
- Add per-event `skipped_counts`.
- Add per-event `error_counts`.
- Add `last_outcome` as one of `success`, `skipped`, or `error`.
- Extend focused status tests for success, search-disabled skip, error, admin
  response shape, and route ownership.
- Add this taskbook, TODO, DEV/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No outbox table.
- No background worker.
- No retry persistence.
- No Elasticsearch dependency changes.
- No endpoint removal or response-field rename.
- No search result ranking or response-shape changes.
- No Item/ECO mutation behavior changes.

## 4. Public Surface

Existing endpoint:

```text
GET /api/v1/search/indexer/status
```

New additive response fields:

- `success_counts`
- `skipped_counts`
- `error_counts`
- `last_outcome`

Existing P4.1 fields remain present.

## 5. Design

The indexer already records event receipt before trying to open a DB session.
This follow-up records the terminal outcome in the shared service wrapper:

- `success` when an enabled search client completes the handler;
- `skipped` when search is disabled or unconfigured;
- `error` when the handler raises.

Each outcome has a per-event counter keyed by the same seven handler names:

- `item.created`
- `item.updated`
- `item.state_changed`
- `item.deleted`
- `eco.created`
- `eco.updated`
- `eco.deleted`

The counters are in-process diagnostics, not durable audit data. They are
intended to help operators distinguish "events are arriving but search is
disabled" from "events are arriving and failing" before introducing any
durable outbox or worker design.

## 6. Acceptance Criteria

- `event_counts` remains present and continues to mean received events.
- The three new outcome-count maps contain all seven handler keys.
- Successful handler execution increments `success_counts`.
- Search-disabled execution increments `skipped_counts` and records
  `search-engine-disabled`.
- Handler exceptions increment `error_counts` while preserving P4.1 error
  redaction.
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

The durable outbox/job-backed indexer remains a separate decision. It should
only start from a new taskbook because it changes persistence, retry, ordering,
and operational recovery semantics.
