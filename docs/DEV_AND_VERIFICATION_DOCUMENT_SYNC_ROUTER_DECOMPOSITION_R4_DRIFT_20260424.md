# DEV AND VERIFICATION - Document Sync Router Decomposition R4 Drift

Date: 2026-04-24

## 1. Scope

R4 moves the C30 document-sync drift/snapshots read surface from the legacy
`document_sync_router.py` into a dedicated router:

- `GET /api/v1/document-sync/drift/overview`
- `GET /api/v1/document-sync/sites/{site_id}/snapshots`
- `GET /api/v1/document-sync/jobs/{job_id}/drift`
- `GET /api/v1/document-sync/export/drift`

The legacy router remains registered and continues to own site/job writes,
mirror operations, baseline/lineage, retention, and freshness/watermark
endpoints.

## 2. Design

The new `document_sync_drift_router.py` follows the staged decomposition pattern
from R1-R3:

- Prefix: `/document-sync`
- Tag: `Document Sync`
- Dependency model: unchanged `get_db` and `get_current_user`
- Service calls: unchanged `DocumentSyncService(db)` pass-through
- Error mapping: existing `ValueError -> 404` behavior preserved for
  job/site-specific drift reads

`app.py` registers split routers in staged order:

1. `document_sync_analytics_router`
2. `document_sync_reconciliation_router`
3. `document_sync_replay_audit_router`
4. `document_sync_drift_router`
5. legacy `document_sync_router`

## 3. Files Changed

- `src/yuantus/meta_engine/web/document_sync_drift_router.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Contracts

`test_document_sync_drift_router_contracts.py` pins:

- all four moved routes are owned by `document_sync_drift_router`
- moved decorators are absent from legacy `document_sync_router.py`
- split router registration precedes legacy router registration
- every moved `(method, path)` is registered exactly once
- `Document Sync` tag is preserved
- the R4 router source declares exactly the four intended C30 paths

The router decomposition portfolio contract now includes the new R4 contract
test in the CI contracts surface.

## 5. Non-Goals

- No full document-sync router closeout.
- No extraction of site/job DTOs or serializers.
- No movement of baseline/lineage, retention, or freshness/watermark routes.
- No movement of core site/job/mirror write paths.
- No service-layer behavior changes.
- No schema, migration, auth, or response contract changes.

## 6. Verification

Completed locally:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/document_sync_analytics_router.py \
  src/yuantus/meta_engine/web/document_sync_reconciliation_router.py \
  src/yuantus/meta_engine/web/document_sync_replay_audit_router.py \
  src/yuantus/meta_engine/web/document_sync_drift_router.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py
```

Result: 86 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py
```

Result: 29 passed.

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

Result: 372 passed.

```bash
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Result: passed.

## 7. Next Router Slices

Recommended continuation order:

1. R5: baseline/lineage router
2. R6: checkpoints/retention router
3. R7: freshness/watermarks router
4. R8: core site/job/mirror router and legacy shell closeout
