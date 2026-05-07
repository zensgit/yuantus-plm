# Development Task - Phase 4 P4.2.2 Search Reports ECO Stage Aging

Date: 2026-05-07

## 1. Goal

Add a second P4.2 reports aggregation surface for ECO operational aging.

P4.2.1 introduced count-based reports summary. P4.2.2 adds an ECO-specific
aging report grouped by current `stage_id`, so operators can identify stages
where ECOs are accumulating without introducing saved reports, dashboards, or
Elasticsearch aggregation scope.

## 2. Scope

- Add `SearchService.eco_stage_aging_report()`.
- Add `GET /api/v1/search/reports/eco-stage-aging`.
- Support JSON output by default.
- Support CSV export through `?format=csv`.
- Require admin authorization for the new route.
- Compute per-stage `count`, `avg_age_days`, and `max_age_days`.
- Add service/router/CSV/ownership tests.
- Update the route-count guard from `674` to `675`.
- Add taskbook, TODO, dev/verification MD, and delivery-doc index entries.

## 3. Non-Goals

- No ECO stage transition history table.
- No stage SLA policy or alerting.
- No Elasticsearch aggregation DSL.
- No saved report persistence.
- No dashboard UI.
- No file/CAD report aggregation.
- No P4.2.1 summary response-shape change.

## 4. Public Surface

New admin route:

```text
GET /api/v1/search/reports/eco-stage-aging
GET /api/v1/search/reports/eco-stage-aging?format=csv
```

JSON response shape:

```json
{
  "engine": "db",
  "age_source": "updated_at_or_created_at",
  "buckets": [
    {
      "key": "review",
      "count": 2,
      "avg_age_days": 3.0,
      "max_age_days": 5.0
    }
  ]
}
```

CSV response columns:

```text
stage,count,avg_age_days,max_age_days
```

## 5. Design

The report is database-backed and uses current ECO rows:

- Group key: `ECO.stage_id`, normalized to `unknown` when null or blank.
- Age timestamp: `ECO.updated_at` first, falling back to `ECO.created_at`.
- Missing timestamp: age `0.0` days.
- Timezone handling: naive datetimes are treated as UTC; aware datetimes are
  normalized to UTC.
- Bucket ordering: descending `count`, then stage key.

The route is separate from `GET /api/v1/search/reports/summary` so P4.2.1's
JSON and CSV contracts remain stable.

## 6. Acceptance Criteria

- Admin user can fetch JSON stage aging report.
- Non-admin user receives `403 Admin role required`.
- CSV export emits `stage,count,avg_age_days,max_age_days`.
- Service returns an empty bucket list when no DB session is available.
- Service falls back from `updated_at` to `created_at`.
- Service normalizes null/blank stage IDs to `unknown`.
- The route is registered once and owned by `search_router`.
- App route count is updated to `675` with an explicit scope note.

## 7. Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/yuantus/meta_engine/services/search_service.py \
  src/yuantus/meta_engine/web/search_router.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_stage_aging.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_reports_eco_stage_aging.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_search_reports_eco_stage_aging.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(len(app.routes))"

git diff --check
```

## 8. Follow-Up

A future P4.2 slice can add SLA policy or trend history, but that requires
explicit product semantics for stage-entered timestamps. This slice only reports
current-row aging from existing columns.
