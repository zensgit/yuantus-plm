# Development Task - Phase 4 P4.1.6 Search Indexer Lag Age Status

Date: 2026-05-06

## 1. Goal

Continue the Phase 4 search-indexer diagnostic chain with a small lag-monitoring
primitive: expose how old the most recent received/success/skipped/error event
timestamps are.

P4.1 through P4.1.5 exposed registration, outcome counters, subscriptions,
lifecycle, health, and Prometheus metrics. Operators can now see whether the
indexer is wired and how many events it has handled, but still need an alertable
freshness value that answers "how long since the last event or successful
indexing action?"

## 2. Scope

- Add `last_event_age_seconds` to `GET /api/v1/search/indexer/status`.
- Add `last_success_age_seconds`.
- Add `last_skipped_age_seconds`.
- Add `last_error_age_seconds`.
- Keep existing `last_*_at` timestamp fields unchanged.
- Add Prometheus gauge samples for non-null age values.
- Keep age values absent from Prometheus when no corresponding event has ever
  occurred.
- Update tests, runtime runbook, TODO, DEV/verification MD, and delivery-doc
  index entries.

## 3. Non-Goals

- No durable outbox table.
- No indexing worker.
- No retry persistence.
- No cross-process lag aggregation.
- No SLA threshold or alert-rule file.
- No Elasticsearch-required local test.
- No CAD material-sync plugin changes.

## 4. Public Surface

Existing admin endpoint:

```text
GET /api/v1/search/indexer/status
```

New additive JSON fields:

- `last_event_age_seconds`
- `last_success_age_seconds`
- `last_skipped_age_seconds`
- `last_error_age_seconds`

Existing metrics endpoint:

```text
GET /api/v1/metrics
```

New additive metric family:

- `yuantus_search_indexer_last_event_age_seconds{kind="event|success|skipped|error"}`

## 5. Design

The search indexer keeps internal `datetime` snapshots alongside the existing
public `last_*_at` ISO strings. This avoids reparsing strings on every status
render and preserves the existing wire-format timestamp fields.

Age values are computed at `indexer_status()` render time using a single
`now` value and are clamped to `>= 0` to avoid negative values from clock skew
or test monkeypatches.

Prometheus rendering only emits age samples when the JSON age field is not
`None`. This avoids sentinel values such as `-1`, which are hard to alert on
correctly and can be mistaken for a real measurement.

## 6. Acceptance Criteria

- Status response contains all four age fields.
- Age fields are `None` before their corresponding event kind has occurred.
- Handler success records event and success ages.
- Handler skip records event and skipped ages.
- Handler error records error age and continues to redact error text.
- Prometheus metrics include non-null age gauges.
- Prometheus metrics omit age gauges for null age values.
- Route count remains unchanged.

## 7. Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/yuantus/meta_engine/services/search_indexer.py \
  src/yuantus/meta_engine/web/search_router.py \
  src/yuantus/observability/metrics.py

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

Durable lag semantics still require outbox/job-backed indexing. This slice is
limited to in-process runtime freshness for the existing event handlers.
