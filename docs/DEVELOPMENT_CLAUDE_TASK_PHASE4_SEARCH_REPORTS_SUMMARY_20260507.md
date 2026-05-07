# Development Task - Phase 4 P4.2.1 Search Reports Summary

Date: 2026-05-07

## 1. Goal

Add the first P4.2 reports aggregation surface on top of the existing search
runtime.

P4.1 closed incremental search-indexer observability. P4.2 starts the reporting
layer requested by the next-cycle plan: aggregate search-relevant inventory by
Item type, Item state, ECO state, and ECO stage. This slice intentionally uses
the database as source of truth and does not change Elasticsearch query
semantics.

## 2. Scope

- Add `SearchService.reports_summary()`.
- Add `GET /api/v1/search/reports/summary`.
- Support JSON output by default.
- Support CSV export through `?format=csv`.
- Require admin authorization for the new route.
- Add focused service/router/CSV/ownership tests.
- Update the route-count guard from 673 to 674.
- Add TODO and dev/verification markdown plus delivery-doc index entries.

## 3. Non-Goals

- No Elasticsearch aggregation DSL.
- No saved-report persistence.
- No scheduled report generation.
- No dashboard UI.
- No file/CAD report aggregation.
- No search indexer event-handler change.
- No CAD material-sync plugin changes.

## 4. Public Surface

New admin route:

```text
GET /api/v1/search/reports/summary
GET /api/v1/search/reports/summary?format=csv
```

JSON response shape:

```json
{
  "engine": "db",
  "items": {
    "total": 0,
    "by_item_type": [],
    "by_state": []
  },
  "ecos": {
    "total": 0,
    "by_state": [],
    "by_stage": []
  }
}
```

CSV response columns:

```text
section,key,count
```

## 5. Design

The aggregation is deliberately DB-backed:

- `Item.item_type_id` feeds `items.by_item_type`.
- `Item.state` feeds `items.by_state`.
- `ECO.state` feeds `ecos.by_state`.
- `ECO.stage_id` feeds `ecos.by_stage`.

Null or blank bucket keys are normalized to `unknown`. Bucket ordering is by
descending count and then key, so repeated exports are stable enough for
operator comparison.

The route uses `response_model=None` because it can return either a Pydantic
JSON response or a `text/csv` response. The JSON branch still validates through
`SearchReportsSummaryResponse` before returning.

## 6. Acceptance Criteria

- Admin user can fetch JSON summary.
- Non-admin user receives `403 Admin role required`.
- CSV export emits `section,key,count` rows.
- Service returns zero totals when no DB session is available.
- Service normalizes null/blank bucket keys to `unknown`.
- The route is registered once and owned by `search_router`.
- App route count is updated to `674` with an explicit scope note.

## 7. Verification Plan

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile \
  src/yuantus/meta_engine/services/search_service.py \
  src/yuantus/meta_engine/web/search_router.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_search_reports_summary.py \
  src/yuantus/meta_engine/tests/test_metrics_router_route_count_delta.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(len(app.routes))"

git diff --check
```

## 8. Follow-Up

P4.2 can continue with richer report slices: item lifecycle trends, ECO stage
aging, file/CAD coverage, or saved report definitions. Those should be separate
PRs because they either add new data sources or introduce persistence.
