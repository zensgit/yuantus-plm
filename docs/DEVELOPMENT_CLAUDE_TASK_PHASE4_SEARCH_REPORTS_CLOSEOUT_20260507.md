# Development Task - Phase 4 P4.2.4 Search Reports Closeout Contracts

Date: 2026-05-07

## 1. Goal

Close out the P4.2 search reports slice by pinning the public surface and
operator documentation for the three DB-backed search report endpoints.

P4.2.1 through P4.2.3 added the runtime routes. P4.2.4 deliberately adds no
runtime behavior. It makes the reports surface harder to accidentally drift.

## 2. Scope

- Add closeout contracts for all `/api/v1/search/reports/*` routes.
- Pin route ownership to `yuantus.meta_engine.web.search_router`.
- Pin exact route set and single registration.
- Pin admin-only behavior.
- Pin response model top-level field sets.
- Pin CSV headers for all three exports.
- Update `docs/RUNBOOK_RUNTIME.md` with search reports operator guidance.
- Add taskbook, TODO, dev/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No new runtime route.
- No SearchService behavior change.
- No response-shape expansion.
- No dashboard UI.
- No saved report persistence.
- No Elasticsearch aggregation DSL.
- No SLA or transition-history semantics.
- No CAD material-sync plugin changes.

## 4. Public Surface Pinned

The closeout contract pins exactly these routes:

```text
GET /api/v1/search/reports/summary
GET /api/v1/search/reports/eco-stage-aging
GET /api/v1/search/reports/eco-state-trend
```

CSV headers pinned:

```text
section,key,count
stage,count,avg_age_days,max_age_days
date,state,count
```

## 5. Design

The closeout contract lives in:

```text
src/yuantus/meta_engine/tests/test_search_reports_closeout_contracts.py
```

It asserts:

- route surface exactly matches the three P4.2 endpoints;
- each route is owned by `search_router`;
- each route is registered exactly once;
- non-admin callers receive `403 Admin role required`;
- response model top-level fields remain stable;
- CSV export headers remain stable;
- `RUNBOOK_RUNTIME.md` documents route names, CSV headers, admin requirement,
  and the `eco-state-trend` interpretation boundary.

## 6. Acceptance Criteria

- No app route-count change from P4.2.3 (`676`).
- Closeout contract passes.
- Existing P4.2 report behavior tests pass.
- Doc-index trio passes.
- Runtime runbook documents all three report endpoints.
- `git diff --check` is clean.

## 7. Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/yuantus/meta_engine/tests/test_search_reports_closeout_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_reports_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_stage_aging.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_state_trend.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_stage_aging.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_state_trend.py \
  src/yuantus/meta_engine/tests/test_search_reports_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(len(app.routes))"

git diff --check
```

## 8. Follow-Up

Future work should not add more `/api/v1/search/reports/*` endpoints without
updating the closeout contract and runbook. SLA or transition-history reporting
requires a separate taskbook because current ECO rows do not store durable
state-entered timestamps.
