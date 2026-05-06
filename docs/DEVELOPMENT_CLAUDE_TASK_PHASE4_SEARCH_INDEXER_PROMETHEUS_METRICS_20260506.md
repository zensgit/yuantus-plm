# Development Task - Phase 4 P4.1.5 Search Indexer Prometheus Metrics

Date: 2026-05-06

## 1. Goal

Expose the existing search indexer status snapshot on the public Prometheus
metrics surface so operators can alert on indexing health without calling the
admin-only JSON endpoint.

P4.1 through P4.1.4 already established a stable, redacted runtime status model
for the incremental search indexer. This slice converts that model into
low-cardinality Prometheus text emitted by `GET /api/v1/metrics`.

## 2. Scope

- Keep `GET /api/v1/search/indexer/status` unchanged.
- Keep the Phase 2 job metric registry renderer unchanged.
- Add a runtime metrics renderer used by the `/metrics` endpoint.
- Emit search indexer registration, uptime, health, index readiness,
  subscription counts, and outcome counters.
- Do not expose `last_error`, event payloads, tenant IDs, org IDs, user IDs, or
  document/item identifiers in metrics.
- Update focused tests, runtime runbook notes, TODO, verification MD, and the
  delivery-doc index.

## 3. Non-Goals

- No new Prometheus dependency.
- No durable outbox table.
- No indexing worker.
- No retry persistence.
- No admin reset endpoint.
- No cross-process metric aggregation.
- No change to CAD material-sync plugin WIP.

## 4. Public Surface

Existing endpoint:

```text
GET /api/v1/metrics
```

New additive metric families:

- `yuantus_search_indexer_registered`
- `yuantus_search_indexer_uptime_seconds`
- `yuantus_search_indexer_health`
- `yuantus_search_indexer_health_reason`
- `yuantus_search_indexer_index_ready`
- `yuantus_search_indexer_subscriptions`
- `yuantus_search_indexer_events_total`

Existing Phase 2 job metric families remain unchanged:

- `yuantus_jobs_total`
- `yuantus_job_duration_ms`

## 5. Design

The registry-level function `render_prometheus_text()` remains job-only so the
Phase 2 downstream-consumer contract continues to pin only the job metric names,
labels, and buckets.

The `/metrics` endpoint now calls `render_runtime_prometheus_text()`, which
joins two sections:

- the existing in-memory job registry;
- a read-only snapshot from `search_indexer.indexer_status()`.

Search indexer metrics use bounded labels:

- `state`: one of `ok`, `not_registered`, `degraded`;
- `reason`: stable health reason strings such as `missing-handlers`;
- `index`: `item` or `eco`;
- `event_type`: the seven expected event names;
- `outcome`: `received`, `success`, `skipped`, or `error`.

This deliberately avoids tenant, org, user, item, ECO, request, and error-text
labels.

## 6. Acceptance Criteria

- Empty job registry still renders an empty string through
  `render_prometheus_text()`.
- `/api/v1/metrics` emits search indexer metrics even when there are no job
  lifecycle events.
- Job metrics and search indexer metrics can appear in the same response.
- The metrics output does not include `last_error` or secret-bearing error
  strings from the status snapshot.
- Existing Phase 2 metric-name and label-cardinality contracts still pass.
- P4 search indexer status tests still pass.

## 7. Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/yuantus/observability/metrics.py \
  src/yuantus/api/routers/metrics.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

## 8. Follow-Up

Durable delivery semantics still require a separate P4 taskbook. This PR only
exports the current in-process search indexer status to the existing metrics
surface.
