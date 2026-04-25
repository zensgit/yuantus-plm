# DEV AND VERIFICATION - Document Sync Router Decomposition R2 Reconciliation

Date: 2026-04-24

## 1. Scope

R2 moves the C24 document-sync reconciliation read surface from the legacy
`document_sync_router.py` into a dedicated router:

- `GET /api/v1/document-sync/reconciliation/queue`
- `GET /api/v1/document-sync/reconciliation/jobs/{job_id}/summary`
- `GET /api/v1/document-sync/reconciliation/sites/{site_id}/status`
- `GET /api/v1/document-sync/export/reconciliation`

The legacy router remains registered and continues to own site/job writes,
mirror operations, replay/audit, drift, lineage, retention, and
freshness/watermark endpoints.

## 2. Design

The new `document_sync_reconciliation_router.py` follows the R1 analytics
pattern:

- Prefix: `/document-sync`
- Tag: `Document Sync`
- Dependency model: unchanged `get_db` and `get_current_user`
- Service calls: unchanged `DocumentSyncService(db)` pass-through
- Error mapping: existing `ValueError -> 404` behavior preserved for
  job/site-specific reconciliation reads

`app.py` registers split routers in staged order:

1. `document_sync_analytics_router`
2. `document_sync_reconciliation_router`
3. legacy `document_sync_router`

## 3. Files Changed

- `src/yuantus/meta_engine/web/document_sync_reconciliation_router.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Contracts

`test_document_sync_reconciliation_router_contracts.py` pins:

- all four moved routes are owned by `document_sync_reconciliation_router`
- moved decorators are absent from legacy `document_sync_router.py`
- split router registration precedes legacy router registration
- every moved `(method, path)` is registered exactly once
- `Document Sync` tag is preserved
- the R2 router source declares exactly the four intended C24 paths

The router decomposition portfolio contract now includes the new R2 contract
test in the CI contracts surface.

## 5. Non-Goals

- No full document-sync router closeout.
- No extraction of site/job DTOs or serializers.
- No movement of replay/audit, drift, lineage, retention, or freshness/watermark
  routes.
- No movement of core site/job/mirror write paths.
- No service-layer behavior changes.
- No schema, migration, auth, or response contract changes.

## 6. Verification

Completed locally:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/document_sync_analytics_router.py \
  src/yuantus/meta_engine/web/document_sync_reconciliation_router.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py
```

Result: 74 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py
```

Result: 17 passed.

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

Result: 360 passed.

```bash
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Result: passed.

## 7. Next Router Slices

Recommended continuation order:

1. R3: replay/audit router
2. R4: drift/snapshots router
3. R5: baseline/lineage router
4. R6: checkpoints/retention router
5. R7: freshness/watermarks router
6. R8: core site/job/mirror router and legacy shell closeout
