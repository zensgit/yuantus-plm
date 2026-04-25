# DEV AND VERIFICATION - Document Sync Router Decomposition R7 Freshness

Date: 2026-04-24

## 1. Scope

R7 moves the C39 document-sync freshness/watermarks read surface from the
legacy `document_sync_router.py` into a dedicated router:

- `GET /api/v1/document-sync/freshness/overview`
- `GET /api/v1/document-sync/watermarks/summary`
- `GET /api/v1/document-sync/sites/{site_id}/freshness`
- `GET /api/v1/document-sync/export/watermarks`

The legacy router remains registered and continues to own only core site/job
and mirror endpoints.

## 2. Design

The new `document_sync_freshness_router.py` follows the staged decomposition
pattern from R1-R6:

- Prefix: `/document-sync`
- Tag: `Document Sync`
- Dependency model: unchanged `get_db` and `get_current_user`
- Service calls: unchanged `DocumentSyncService(db)` pass-through
- Error mapping: existing `ValueError -> 404` behavior preserved for
  site-specific freshness reads

`app.py` registers split routers in staged order:

1. `document_sync_analytics_router`
2. `document_sync_reconciliation_router`
3. `document_sync_replay_audit_router`
4. `document_sync_drift_router`
5. `document_sync_lineage_router`
6. `document_sync_retention_router`
7. `document_sync_freshness_router`
8. legacy `document_sync_router`

CI contract lists and portfolio entries remain path-sorted per repository
sorting contracts. That order is maintenance order only; runtime ownership is
controlled by the `app.py` registration order above and pinned by router
contract tests.

## 3. Files Changed

- `src/yuantus/meta_engine/web/document_sync_freshness_router.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Contracts

`test_document_sync_freshness_router_contracts.py` pins:

- all four moved routes are owned by `document_sync_freshness_router`
- moved decorators are absent from legacy `document_sync_router.py`
- split router registration precedes legacy router registration
- every moved `(method, path)` is registered exactly once
- `Document Sync` tag is preserved
- the R7 router source declares exactly the four intended C39 paths

The router decomposition portfolio contract now includes the new R7 contract
test in the CI contracts surface.

## 5. Non-Goals

- No full document-sync router closeout in R7.
- No extraction of site/job DTOs or serializers.
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
  src/yuantus/meta_engine/web/document_sync_lineage_router.py \
  src/yuantus/meta_engine/web/document_sync_retention_router.py \
  src/yuantus/meta_engine/web/document_sync_freshness_router.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_lineage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_retention_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py
```

Result: 104 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_lineage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_retention_router_contracts.py
```

Result: 47 passed.

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

Result: 400 passed.

```bash
bash -n scripts/verify_odoo18_plm_stack.sh
git diff --check
```

Result: passed.

## 7. Next Router Slice

Recommended continuation:

1. R8: core site/job/mirror router and legacy shell closeout
