# DEV AND VERIFICATION - Document Sync Router Decomposition R1 Analytics

Date: 2026-04-24

## 1. Scope

R1 moves the C21 document-sync analytics/export read surface from the legacy
`document_sync_router.py` into a dedicated router:

- `GET /api/v1/document-sync/overview`
- `GET /api/v1/document-sync/sites/{site_id}/analytics`
- `GET /api/v1/document-sync/jobs/{job_id}/conflicts`
- `GET /api/v1/document-sync/export/overview`
- `GET /api/v1/document-sync/export/conflicts`

The legacy router remains registered and continues to own site/job writes,
mirror operations, reconciliation, replay/audit, drift, lineage, retention, and
freshness/watermark endpoints.

## 2. Design

The new `document_sync_analytics_router.py` uses the same prefix and tag as the
legacy router:

- Prefix: `/document-sync`
- Tag: `Document Sync`
- Dependency model: unchanged `get_db` and `get_current_user`
- Service calls: unchanged `DocumentSyncService(db)` pass-through
- Error mapping: existing `ValueError -> 404` behavior preserved for
  site/job-specific analytics reads

`app.py` registers the split analytics router before the legacy router to pin
route ownership and avoid duplicate legacy ownership during the staged
decomposition.

## 3. Files Changed

- `src/yuantus/meta_engine/web/document_sync_analytics_router.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Contracts

`test_document_sync_analytics_router_contracts.py` pins:

- all five moved routes are owned by `document_sync_analytics_router`
- moved decorators are absent from legacy `document_sync_router.py`
- split router registration precedes legacy router registration
- every moved `(method, path)` is registered exactly once
- `Document Sync` tag is preserved
- the R1 router source declares exactly the five intended C21 paths

The router decomposition portfolio contract now includes the new contract test
in the CI contracts surface.

`verify_odoo18_plm_stack.sh` now defaults pytest execution to
`$PY_BIN -m pytest` instead of `.venv/bin/pytest`. This keeps the script
portable when a copied local venv contains a stale pytest entrypoint shebang,
while still allowing `PYTEST_BIN=...` explicit override.

## 5. Non-Goals

- No full document-sync router closeout.
- No extraction of site/job DTOs or serializers.
- No movement of reconciliation, replay/audit, drift, lineage, retention, or
  freshness/watermark routes.
- No service-layer behavior changes.
- No schema, migration, auth, or response contract changes.

## 6. Verification

Completed locally:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/document_sync_analytics_router.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py
```

Result: 68 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py
```

Result: 11 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: 3 passed.

```bash
bash scripts/verify_odoo18_plm_stack.sh smoke
```

Result: 265 passed.

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
```

Result: 354 passed.

```bash
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Result: passed.

## 7. Next Router Slices

Recommended continuation order:

1. R2: reconciliation router (`/reconciliation/*`, `/export/reconciliation`)
2. R3: replay/audit router
3. R4: drift/snapshots router
4. R5: baseline/lineage router
5. R6: checkpoints/retention router
6. R7: freshness/watermarks router
7. R8: core site/job/mirror router and legacy shell closeout
