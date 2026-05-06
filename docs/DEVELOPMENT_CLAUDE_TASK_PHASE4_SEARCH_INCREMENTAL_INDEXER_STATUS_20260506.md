# Development Task - Phase 4 P4.1 Search Incremental Indexer Status

Date: 2026-05-06

## 1. Goal

Start Phase 4 P4.1 with the smallest useful production diagnostic slice for
incremental search indexing.

The repository already had an event-driven Item/ECO search indexer registered
at application startup. The gap was observability: operators could see whether
the Elasticsearch index existed, but not whether the incremental event indexer
was registered, receiving events, skipping because search was disabled, or
failing.

## 2. Scope

- Add in-process runtime counters to `search_indexer.py`.
- Expose the counters through an admin-only search endpoint.
- Add focused tests for handler coverage, status updates, authorization, and
  route ownership.
- Redact sensitive values from the last-error diagnostic field.
- Add this taskbook, TODO, DEV/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No outbox table.
- No background worker.
- No Elasticsearch dependency changes.
- No search result scoring changes.
- No Item/ECO mutation behavior changes.
- No file/document/BOM mutation indexing in this slice.
- No Phase 4 reports/RPC implementation.

## 4. Public Surface

New endpoint:

```text
GET /api/v1/search/indexer/status
```

Access:

- admin-only via the shared `require_admin_user` dependency.

Response fields:

- `registered`
- `item_index_ready`
- `eco_index_ready`
- `handlers`
- `event_counts`
- `last_event_type`
- `last_event_at`
- `last_success_event_type`
- `last_success_at`
- `last_skipped_event_type`
- `last_skipped_at`
- `last_skipped_reason`
- `last_error_event_type`
- `last_error_at`
- `last_error`

## 5. Design

The status is intentionally in-process and diagnostic-only.

The existing indexer still subscribes to:

- `item.created`
- `item.updated`
- `item.state_changed`
- `item.deleted`
- `eco.created`
- `eco.updated`
- `eco.deleted`

Each handler now records receipt before opening a DB session. The shared
service wrapper records:

- success when the handler completes against an enabled search client;
- skip when search is disabled or unconfigured;
- error when the handler raises.

This keeps default local/dev behavior unchanged: when no search engine is
configured, events are observed and counted, but indexing remains a no-op.

`last_error` intentionally stores the exception type plus a shortened,
redacted message. It must not expose connection-string passwords, tokens, or
secret-like key/value fields through the admin diagnostic response.

## 6. Acceptance Criteria

- The endpoint is registered exactly once and owned by `search_router`.
- Non-admin users receive 403.
- Admin users can read the status payload.
- Handler list contains all seven Item/ECO incremental event handlers.
- Event receipt increments the matching event counter.
- Error status redacts secret-like values.
- Existing DB fallback search behavior is unchanged.

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

git diff --check
```

## 8. Follow-Up

P4.1 follow-up can add durable outbox/job-backed indexing if production
evidence shows in-process event indexing is insufficient. That should be a
separate taskbook because it changes persistence and retry semantics.
