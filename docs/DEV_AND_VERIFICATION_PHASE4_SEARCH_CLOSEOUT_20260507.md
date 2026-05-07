# Dev & Verification - Phase 4 Search Closeout

Date: 2026-05-07

## 1. Summary

Implemented P4.3, the closeout slice for Phase 4 (Search incremental +
reports). This PR adds closeout contracts and documentation only. It does not
change runtime code.

Phase 4 now has two closed implementation tracks:

- P4.1 search-indexer diagnostics and metrics.
- P4.2 search reports aggregation and CSV export.

P4.3 pins the final route, schema, metrics, and operator-runbook surface so
future changes require an intentional contract update.

## 2. Files Changed

- `src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py`
- `.github/workflows/ci.yml`
- `docs/RUNBOOK_RUNTIME.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE4_SEARCH_CLOSEOUT_20260507.md`
- `docs/PHASE4_SEARCH_CLOSEOUT_TODO_20260507.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_CLOSEOUT_20260507.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The P4.3 contract covers the final Phase 4 surface:

| Area | Surface |
| --- | --- |
| Search-indexer status | `GET /api/v1/search/indexer/status` |
| Search-indexer metrics | `/api/v1/metrics` emits `yuantus_search_indexer_*` families |
| Search reports | `GET /api/v1/search/reports/summary` |
| Search reports | `GET /api/v1/search/reports/eco-stage-aging` |
| Search reports | `GET /api/v1/search/reports/eco-state-trend` |

The contract asserts:

- routes are registered exactly once and owned by the expected module;
- app route count remains `676`;
- `SearchIndexerStatusResponse` has the final P4.1 field set;
- indexed domain events and intentionally unindexed events remain explicit;
- search-indexer Prometheus labels stay low-cardinality;
- `RUNBOOK_RUNTIME.md` documents both search-indexer metrics and reports;
- the search-indexer metrics runbook section names the admin JSON endpoint it
  mirrors: `GET /api/v1/search/indexer/status`;
- this closeout MD links the P4.1/P4.2 evidence chain and records the Phase 5
  pause gate.

## 4. Evidence Chain

P4.1 search-indexer track:

- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INCREMENTAL_INDEXER_STATUS_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_OUTCOME_COUNTERS_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_SUBSCRIPTION_STATUS_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_LIFECYCLE_STATUS_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_HEALTH_SUMMARY_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_PROMETHEUS_METRICS_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_LAG_AGE_STATUS_20260506.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_INDEXER_EVENT_COVERAGE_STATUS_20260507.md`

P4.2 search reports track:

- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_REPORTS_SUMMARY_20260507.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_REPORTS_ECO_STAGE_AGING_20260507.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_REPORTS_ECO_STATE_TREND_20260507.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_REPORTS_CLOSEOUT_20260507.md`

P4.3 closeout artifact:

- `src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_CLOSEOUT_20260507.md`

## 5. Safety Boundaries

- No runtime code changes.
- No route-count change.
- No search ranking or report aggregation behavior change.
- No Elasticsearch-required test or query implementation.
- No dashboard, alert, saved report, or UI scope.
- No CAD material-sync plugin changes.
- Phase 5 requires explicit opt-in and is not started by this closeout.

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_search_incremental_indexer_status.py \
  src/yuantus/api/tests/test_observability_metrics_registry.py \
  src/yuantus/api/tests/test_metrics_endpoint.py \
  src/yuantus/meta_engine/tests/test_search_reports_closeout_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_job_wiring.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/yuantus-python-cli-redaction/src \
  /Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -c \
  "from yuantus.api.app import create_app; app=create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

## 7. Verification Results

- `py_compile`: passed.
- P4.1/P4.2/P4.3 focused suite: 38 passed.
- CI wiring plus doc/runbook index contracts: 6 passed.
- Boot check: `routes=676 middleware=4`.
- `git diff --check`: clean.

## 8. Remaining Work

Phase 4 implementation and closeout are complete after this PR merges.

Phase 5 requires explicit opt-in. The next phase must not be auto-started from
this closeout branch.
