# Development Task - Phase 4 Search Closeout

Date: 2026-05-07

## 1. Goal

Close Phase 4 (Search incremental + reports) with a contract-only PR that pins
the final public and operator-facing surface delivered across P4.1 and P4.2.

This task is deliberately non-runtime. P4.1 and P4.2 already delivered the
behavioral changes. P4.3 adds regression-prevention contracts and a final
development/verification record.

## 2. Scope

- Add one Phase 4 closeout contract test file.
- Add one final Phase 4 development and verification MD.
- Add one small TODO record for the closeout execution.
- Register the new contract in the CI `contracts` job.
- Add the new docs to `docs/DELIVERY_DOC_INDEX.md`.
- Clarify the `RUNBOOK_RUNTIME.md` search-indexer metrics section with the
  admin JSON status endpoint it mirrors.

## 3. Public Surface To Pin

P4.1 search-indexer diagnostics:

- `GET /api/v1/search/indexer/status`
- `GET /api/v1/metrics` search-indexer metric families

P4.2 search reports:

- `GET /api/v1/search/reports/summary`
- `GET /api/v1/search/reports/eco-stage-aging`
- `GET /api/v1/search/reports/eco-state-trend`

## 4. Contract Assertions

The closeout contract must assert:

- the Phase 4 route surface is registered exactly once;
- route ownership remains in `search_router` except `/api/v1/metrics`;
- final app route count remains `676`;
- `SearchIndexerStatusResponse` field set is unchanged;
- indexed and intentionally unindexed domain-event lists are unchanged;
- search-indexer Prometheus metric names and labels stay low-cardinality;
- `RUNBOOK_RUNTIME.md` documents the final search-indexer and report surfaces;
- the final Phase 4 closeout MD links the P4.1/P4.2 evidence chain and states
  that Phase 5 requires explicit opt-in.

## 5. Non-Goals

- No SearchService behavior change.
- No search-indexer event handler change.
- No new route or route-count change.
- No Elasticsearch query implementation.
- No dashboards, alerts, or UI.
- No Phase 5 startup.
- No CAD material-sync plugin changes.

## 6. Verification

Run:

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

## 7. Output Files

- `src/yuantus/meta_engine/tests/test_phase4_search_closeout_contracts.py`
- `.github/workflows/ci.yml`
- `docs/RUNBOOK_RUNTIME.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE4_SEARCH_CLOSEOUT_20260507.md`
- `docs/PHASE4_SEARCH_CLOSEOUT_TODO_20260507.md`
- `docs/DEV_AND_VERIFICATION_PHASE4_SEARCH_CLOSEOUT_20260507.md`
- `docs/DELIVERY_DOC_INDEX.md`
