# Dev & Verification - Phase 4 Search Indexer Prometheus Metrics

Date: 2026-05-06

## 1. Summary

Implemented P4.1.5: search indexer status is now exported through the existing
Prometheus endpoint.

The change is additive and keeps the admin JSON status endpoint intact. The
existing Phase 2 job registry renderer remains job-only; the `/api/v1/metrics`
route uses a new runtime renderer that combines job metrics with a read-only
search indexer status snapshot.

## 2. Files Changed

- `src/yuantus/observability/metrics.py`
- `src/yuantus/api/routers/metrics.py`
- `src/yuantus/api/tests/test_observability_metrics_registry.py`
- `src/yuantus/api/tests/test_metrics_endpoint.py`
- `src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py`
- `docs/RUNBOOK_RUNTIME.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE4_SEARCH_INDEXER_PROMETHEUS_METRICS_20260506.md`
- `docs/PHASE4_SEARCH_INDEXER_PROMETHEUS_METRICS_TODO_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_PROMETHEUS_METRICS_20260506.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

New public renderer:

- `render_runtime_prometheus_text()`: endpoint-level renderer that joins the
  existing job registry and the search indexer snapshot.

Existing public renderer preserved:

- `render_prometheus_text()`: still returns only Phase 2 job metrics. This
  keeps registry-level tests and closeout contracts focused on the original
  job metric cardinality contract.

New search indexer metric families:

- `yuantus_search_indexer_registered`
- `yuantus_search_indexer_uptime_seconds`
- `yuantus_search_indexer_health`
- `yuantus_search_indexer_health_reason`
- `yuantus_search_indexer_index_ready`
- `yuantus_search_indexer_subscriptions`
- `yuantus_search_indexer_events_total`

## 4. Safety Boundaries

- No new runtime dependency.
- No route-count change.
- No mutation of indexer status state from metrics rendering.
- No `last_error` or secret-bearing error text emitted in metrics.
- No high-cardinality tenant/org/user/item/ECO labels.
- No durable outbox, worker, retry, or replay behavior.
- Route count remains `673`; this slice adds no route.
- Primary CAD material-sync worktree was left untouched; this work ran in a
  temporary worktree.

## 5. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m py_compile \
  src/yuantus/observability/metrics.py \
  src/yuantus/api/routers/metrics.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/api/tests/test_phase2_observability_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
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
- Focused metrics/search/P2 contracts: 33 passed.
- Focused doc-index regression: 29 passed.
- Boot check: `routes=673 middleware=4`.
- `git diff --check`: clean.

## 7. Non-Goals

- No durable search outbox.
- No background search indexing worker.
- No retry persistence.
- No Elasticsearch-required tests.
- No request logging changes.
- No CAD material-sync plugin changes.
