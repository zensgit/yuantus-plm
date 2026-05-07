# Development Task - Phase 4 P4.2.3 Search Reports ECO State Trend

Date: 2026-05-07

## 1. Goal

Add a DB-backed ECO state trend report for P4.2 reporting.

P4.2.1 added count summaries and P4.2.2 added current-stage aging. P4.2.3 adds
time-windowed trend buckets based on ECO creation date and current state, giving
operators a simple view of recent ECO intake by state without implying stage or
state transition history.

## 2. Scope

- Add `SearchService.eco_state_trend_report()`.
- Add `GET /api/v1/search/reports/eco-state-trend`.
- Support `days` query parameter with bounds `1..366`.
- Support JSON output by default.
- Support CSV export through `?format=csv`.
- Require admin authorization for the new route.
- Add service/router/CSV/query-validation/ownership tests.
- Update route-count guard from `675` to `676`.
- Add taskbook, TODO, dev/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No ECO state transition history.
- No lifecycle event reconstruction.
- No SLA thresholds or alerts.
- No Elasticsearch aggregation DSL.
- No saved report persistence.
- No dashboard UI.
- No P4.2.1 or P4.2.2 response-shape change.

## 4. Public Surface

New admin route:

```text
GET /api/v1/search/reports/eco-state-trend
GET /api/v1/search/reports/eco-state-trend?days=7
GET /api/v1/search/reports/eco-state-trend?days=7&format=csv
```

JSON response shape:

```json
{
  "engine": "db",
  "trend_source": "created_at_current_state",
  "days": 7,
  "start_date": "2026-05-01",
  "end_date": "2026-05-07",
  "buckets": [
    {"date": "2026-05-06", "state": "draft", "count": 2}
  ]
}
```

CSV response columns:

```text
date,state,count
```

## 5. Design

The report is database-backed and uses current ECO rows:

- Window: UTC calendar days ending at `now`.
- Default `days`: `30`.
- Bounds: `1..366`, enforced at the router.
- Timestamp: `ECO.created_at`.
- Group key: `created_at` UTC date plus current `ECO.state`.
- Null/blank state: `unknown`.
- Missing `created_at`: ignored because the report is explicitly creation-date
  based.

This is an intake/current-state report, not a transition report. It does not
answer "when did this ECO enter this state" because the current model has no
state transition history table.

## 6. Acceptance Criteria

- Admin user can fetch JSON trend report.
- Non-admin user receives `403 Admin role required`.
- CSV export emits `date,state,count`.
- `days=367` is rejected with `422`.
- Service returns empty buckets when no DB session is available.
- Service normalizes null/blank state to `unknown`.
- The route is registered once and owned by `search_router`.
- App route count is updated to `676` with an explicit scope note.

## 7. Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/yuantus/meta_engine/services/search_service.py \
  src/yuantus/meta_engine/web/search_router.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_state_trend.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_reports_eco_state_trend.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_stage_aging.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_stage_aging.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_state_trend.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(len(app.routes))"

git diff --check
```

## 8. Follow-Up

True state-transition trend reporting requires a durable lifecycle history or
event table. That should be a separate design task, not inferred from current
row state.
