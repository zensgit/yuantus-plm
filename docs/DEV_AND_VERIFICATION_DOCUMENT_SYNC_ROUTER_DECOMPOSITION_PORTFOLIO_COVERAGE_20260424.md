# DEV AND VERIFICATION - Document Sync Router Decomposition Portfolio Coverage

Date: 2026-04-24

## 1. Scope

After R8 closeout, `document_sync_router.py` became a registered compatibility
shell with no runtime route handlers. This increment adds that shell to the
global router decomposition portfolio contract so the closeout is enforced both
locally and in the shared portfolio gate.

## 2. Design

`test_router_decomposition_portfolio_contracts.py` already tracks legacy router
shells through `LEGACY_ROUTER_STATES`. The Document Sync shell now uses the same
contract pattern as approvals, BOM, box, CAD, cutted-parts, maintenance,
quality, report, and subcontracting:

- `legacy_module`: `yuantus.meta_engine.web.document_sync_router`
- `registered`: `True`
- `include_token`: `app.include_router(document_sync_router`
- `import_token`: `from yuantus.meta_engine.web.document_sync_router import document_sync_router`

This keeps the legacy import surface available while asserting that no runtime
route is owned by the legacy module.

## 3. Files Changed

- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_DOCUMENT_SYNC_ROUTER_DECOMPOSITION_PORTFOLIO_COVERAGE_20260424.md`

## 4. Contracts

The portfolio contract now additionally asserts for `document_sync_router.py`:

- legacy module declares no `@document_sync_router.*` route decorators
- legacy shell stays imported and registered intentionally
- no app route endpoint module resolves to `yuantus.meta_engine.web.document_sync_router`

## 5. Non-Goals

- No runtime route movement; R8 already moved the remaining Document Sync routes.
- No removal of `document_sync_router.py`.
- No app registration change.
- No service-layer, schema, auth, or response contract changes.

## 6. Verification

Completed locally:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py
```

Result: 4 passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_document_sync_router_decomposition_closeout_contracts.py
```

Result: 9 passed.

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
