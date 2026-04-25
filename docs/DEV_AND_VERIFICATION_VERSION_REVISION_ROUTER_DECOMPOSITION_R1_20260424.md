# Version Router Decomposition R1 - Revision Schemes and Utilities - 2026-04-24

## 1. Scope

This increment moves revision scheme and revision utility routes out of `version_router.py` into `version_revision_router.py`.

The legacy `version_router.py` remains registered and continues to own checkout, checkin, merge, file, iteration, tree, history, and effectivity routes.

## 2. Runtime Modules

- `src/yuantus/meta_engine/web/version_revision_router.py`
- `src/yuantus/meta_engine/web/version_router.py`

## 3. Moved Routes

- `POST /api/v1/versions/schemes`
- `GET /api/v1/versions/schemes`
- `GET /api/v1/versions/schemes/for-type/{item_type_id}`
- `GET /api/v1/versions/revision/next`
- `GET /api/v1/versions/revision/parse`
- `GET /api/v1/versions/revision/compare`

## 4. App Registration

`src/yuantus/api/app.py` now registers `version_revision_router` before `version_router`.

This keeps public paths stable while allowing the first low-risk version route group to be owned by a focused module.

## 5. Tests Added

- `src/yuantus/meta_engine/tests/test_version_revision_router_contracts.py`
- `src/yuantus/meta_engine/tests/test_version_revision_router.py`

## 6. CI Wiring

The new route ownership contract is included in `.github/workflows/ci.yml`.

This is not yet a version router closeout. `version_router.py` still intentionally owns the remaining version routes.

## 7. Verification

Commands run:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/version_revision_router.py \
  src/yuantus/meta_engine/web/version_router.py \
  src/yuantus/api/app.py
```

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_version_revision_router_contracts.py \
  src/yuantus/meta_engine/tests/test_version_revision_router.py \
  src/yuantus/meta_engine/tests/test_version_service.py \
  src/yuantus/meta_engine/tests/test_version_advanced.py \
  src/yuantus/meta_engine/tests/test_version_checkout_checkin_router.py \
  src/yuantus/meta_engine/tests/test_version_merge_router.py \
  src/yuantus/meta_engine/tests/test_version_file_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_source_checkout_router.py \
  src/yuantus/meta_engine/tests/test_version_router_doc_sync_gate.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

```bash
.venv/bin/python -m pytest -q src/yuantus/meta_engine/tests/test_*router*_contracts.py
```

```bash
git diff --check
```

Observed results:

- `py_compile`: passed
- Version R1 focused regression: `58 passed in 11.65s`
- Version R1+R2 focused regression after iteration split: `67 passed in 12.49s`
- Full router contract sweep: `302 passed in 47.55s`
- Full router contract sweep after iteration split: `308 passed in 46.76s`
- `git diff --check`: passed

## 8. Non-Goals

- No public route path changes.
- No checkout/checkin behavior changes.
- No version file lock behavior changes.
- No merge, branch, revise, iteration, tree, history, or effectivity route changes.
- No service-layer changes.
- No database or migration changes.

## 9. Next Version Slices

Recommended next slices:

- R2: iteration routes
- R3: version file routes
- R4: core lifecycle routes, including init, checkout, checkin, branch, merge, revise, history, tree, effective, and effectivity
