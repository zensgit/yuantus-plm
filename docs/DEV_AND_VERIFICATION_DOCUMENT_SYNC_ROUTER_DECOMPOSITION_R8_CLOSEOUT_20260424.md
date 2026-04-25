# DEV AND VERIFICATION - Document Sync Router Decomposition R8 Closeout

Date: 2026-04-24

## 1. Scope

R8 moves the remaining Document Sync core runtime surface from the legacy
`document_sync_router.py` into `document_sync_core_router.py`:

- `POST /api/v1/document-sync/sites`
- `GET /api/v1/document-sync/sites`
- `GET /api/v1/document-sync/sites/{site_id}`
- `POST /api/v1/document-sync/sites/{site_id}/mirror-probe`
- `POST /api/v1/document-sync/sites/{site_id}/mirror-execute`
- `POST /api/v1/document-sync/jobs`
- `GET /api/v1/document-sync/jobs`
- `GET /api/v1/document-sync/jobs/{job_id}`
- `GET /api/v1/document-sync/jobs/{job_id}/summary`

The legacy `document_sync_router.py` is now an empty compatibility shell with
no route decorators. It remains registered so older imports and R1-R7 staged
registration contracts stay stable.

## 2. Design

`document_sync_core_router.py` preserves the existing core behavior:

- Prefix: `/document-sync`
- Tag: `Document Sync`
- DTOs: `SiteCreateRequest` and `JobCreateRequest` moved unchanged
- Serializers: `_site_dict` and `_job_dict` moved unchanged
- Dependency model: unchanged `get_db` and `get_current_user`
- Service calls: unchanged `DocumentSyncService(db)` pass-through
- Error mapping: existing `ValueError -> 400/404` behavior preserved
- Transaction behavior: existing `db.commit()` and `db.rollback()` behavior
  preserved for site/job writes and mirror execute

`app.py` registers document-sync routers in decomposition order:

1. `document_sync_analytics_router`
2. `document_sync_reconciliation_router`
3. `document_sync_replay_audit_router`
4. `document_sync_drift_router`
5. `document_sync_lineage_router`
6. `document_sync_retention_router`
7. `document_sync_freshness_router`
8. `document_sync_core_router`
9. legacy `document_sync_router` shell

CI contract lists and portfolio entries remain path-sorted per repository
sorting contracts. Runtime ownership is controlled by `app.py` registration
order and pinned by router contract tests.

## 3. Files Changed

- `src/yuantus/meta_engine/web/document_sync_core_router.py`
- `src/yuantus/meta_engine/web/document_sync_router.py`
- `src/yuantus/api/app.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router.py`
- `src/yuantus/meta_engine/tests/test_document_sync_core_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py`
- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `.github/workflows/ci.yml`
- `scripts/verify_odoo18_plm_stack.sh`
- `docs/DELIVERY_DOC_INDEX.md`

## 4. Contracts

`test_document_sync_core_router_contracts.py` pins:

- all nine core routes are owned by `document_sync_core_router`
- moved decorators are absent from legacy `document_sync_router.py`
- core router registration precedes legacy shell registration
- every moved `(method, path)` is registered exactly once
- `Document Sync` tag is preserved
- the R8 router source declares exactly the intended core paths

`test_document_sync_router_decomposition_closeout_contracts.py` pins:

- all 38 `/api/v1/document-sync/*` routes have explicit split router owners
- every Document Sync route is registered exactly once
- the legacy module is shell-only and declares no route handlers
- `app.py` preserves the full Document Sync router registration order

## 5. Non-Goals

- No service-layer behavior changes.
- No schema, migration, auth, or response contract changes.
- No removal of the legacy `document_sync_router` import surface.
- No reshaping of DTOs or serializers.
- No changes outside Document Sync routing, CI wiring, and documentation.

## 6. Verification

Completed locally:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/document_sync_analytics_router.py \
  src/yuantus/meta_engine/web/document_sync_core_router.py \
  src/yuantus/meta_engine/web/document_sync_reconciliation_router.py \
  src/yuantus/meta_engine/web/document_sync_replay_audit_router.py \
  src/yuantus/meta_engine/web/document_sync_drift_router.py \
  src/yuantus/meta_engine/web/document_sync_lineage_router.py \
  src/yuantus/meta_engine/web/document_sync_retention_router.py \
  src/yuantus/meta_engine/web/document_sync_freshness_router.py \
  src/yuantus/meta_engine/web/document_sync_router.py \
  src/yuantus/api/app.py \
  src/yuantus/meta_engine/tests/test_document_sync_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_document_sync_router.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_lineage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_retention_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py
```

Result: 114 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_document_sync_analytics_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_core_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_drift_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_freshness_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_lineage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_reconciliation_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_replay_audit_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_retention_router_contracts.py \
  src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py
```

Result: 57 passed.

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

## 7. Closeout State

Document Sync router decomposition is complete:

- R1 analytics/export
- R2 reconciliation
- R3 replay/audit
- R4 drift/snapshots
- R5 baseline/lineage
- R6 checkpoints/retention
- R7 freshness/watermarks
- R8 core site/job/mirror + legacy shell
