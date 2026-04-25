# DEV AND VERIFICATION - Version Router Decomposition Portfolio Coverage

Date: 2026-04-24

## 1. Scope

After Version router closeout, `version_router.py` became a registered
compatibility shell with no runtime route handlers. This increment adds that
shell and its Version route contract tests to the global router decomposition
portfolio contract.

## 2. Design

`test_router_decomposition_portfolio_contracts.py` now tracks Version through
the same legacy-shell inventory used by other decomposed router families:

- `legacy_module`: `yuantus.meta_engine.web.version_router`
- `registered`: `True`
- `include_token`: `app.include_router(version_router`
- `import_token`: `from yuantus.meta_engine.web.version_router import version_router`

The portfolio also now requires CI coverage for:

- `test_version_revision_router_contracts.py`
- `test_version_iteration_router_contracts.py`
- `test_version_file_router_contracts.py`
- `test_version_lifecycle_router_contracts.py`
- `test_version_effectivity_router_contracts.py`
- `test_version_router_decomposition_closeout_contracts.py`

CI already listed these files; this change makes the portfolio gate enforce
that they remain present.

## 3. Files Changed

- `src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_VERSION_ROUTER_DECOMPOSITION_PORTFOLIO_COVERAGE_20260424.md`

## 4. Contracts

The portfolio contract now additionally asserts for `version_router.py`:

- legacy module declares no `@version_router.*` route decorators
- legacy shell stays imported and registered intentionally
- no app route endpoint module resolves to `yuantus.meta_engine.web.version_router`
- all Version split/closeout contract tests stay wired into the CI contract job

## 5. Non-Goals

- No runtime route movement; Version closeout already moved the remaining routes.
- No removal of `version_router.py`.
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
  src/yuantus/meta_engine/tests/test_version_router_decomposition_closeout_contracts.py
```

Result: 8 passed.

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
