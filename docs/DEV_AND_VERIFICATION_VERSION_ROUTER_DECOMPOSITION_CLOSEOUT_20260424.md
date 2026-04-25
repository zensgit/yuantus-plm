# Version Router Decomposition Closeout

Date: 2026-04-24

## 1. Scope

This closeout completes the Version router decomposition. The remaining
effectivity/read routes are split from the legacy `version_router.py` into
`version_effectivity_router.py`, and `version_router.py` becomes an empty
compatibility shell.

Moved routes:

- `POST /api/v1/versions/{version_id}/effectivity`
- `GET /api/v1/versions/items/{item_id}/effective`
- `GET /api/v1/versions/items/{item_id}/tree`

## 2. Final Route Ownership

Version route ownership after closeout:

- `version_revision_router`: schemes and revision utility routes.
- `version_iteration_router`: iteration create/list/latest/restore/delete routes.
- `version_file_router`: file binding, file lock, full compare, and full tree routes.
- `version_lifecycle_router`: init, checkout, checkin, merge, compare, revise, history, and branch routes.
- `version_effectivity_router`: effectivity, effective version, and basic version tree routes.
- `version_router`: empty compatibility shell only.

The application registration order is:

1. `version_revision_router`
2. `version_iteration_router`
3. `version_file_router`
4. `version_lifecycle_router`
5. `version_effectivity_router`
6. `version_router`

## 3. Runtime Changes

- Added `src/yuantus/meta_engine/web/version_effectivity_router.py`.
- Converted `src/yuantus/meta_engine/web/version_router.py` to an empty shell.
- Registered `version_effectivity_router` in `src/yuantus/api/app.py`.
- Added focused behavior tests for effectivity, effective version, and tree routes.
- Added closeout contracts for final `/api/v1/versions/*` ownership.

No service logic, schema, migration, auth policy, or response shape was changed.

## 4. Contracts

Added:

- `test_version_effectivity_router_contracts.py`
- `test_version_router_decomposition_closeout_contracts.py`

The contracts assert:

- all 3 R5 routes are owned by `version_effectivity_router`;
- `version_router.py` declares no route decorators;
- all known `/api/v1/versions/*` routes are owned by split routers;
- the legacy shell is registered after every split Version router.

The new contract tests are registered in `.github/workflows/ci.yml`.

## 5. Verification

Py compile:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/version_effectivity_router.py \
  src/yuantus/meta_engine/web/version_lifecycle_router.py \
  src/yuantus/meta_engine/web/version_file_router.py \
  src/yuantus/meta_engine/web/version_iteration_router.py \
  src/yuantus/meta_engine/web/version_revision_router.py \
  src/yuantus/meta_engine/web/version_router.py \
  src/yuantus/api/app.py
```

Result: passed.

Focused Version regression:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_effectivity_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_effectivity_router.py \
  src/yuantus/meta_engine/tests/test_version_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_version_lifecycle_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_file_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_iteration_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_iteration_router.py \
  src/yuantus/meta_engine/tests/test_version_revision_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_revision_router.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_advanced.py \
  src/yuantus/meta_engine/tests/test_version_checkout_checkin_router.py \
  src/yuantus/meta_engine/tests/test_version_merge_router.py \
  src/yuantus/meta_engine/tests/test_version_source_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `94 passed in 17.85s`.

Full router contract sweep:

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
```

Result: `328 passed in 48.01s`.

Doc index contracts:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `3 passed in 0.02s`.

Diff whitespace check:

```bash
git diff --check
```

Result: passed.

## 6. Explicit Non-Goals

- Do not change VersionService behavior.
- Do not change checkout doc-sync semantics.
- Do not change response payloads.
- Do not remove the legacy `version_router` import surface.

## 7. Closeout Result

The Version router line is fully decomposed. The legacy router is now a
compatibility shell and the route map is pinned by a closeout contract.
