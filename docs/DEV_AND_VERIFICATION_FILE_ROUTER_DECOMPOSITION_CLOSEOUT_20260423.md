# File Router Decomposition Closeout

Date: 2026-04-23

## 1. Scope

This closeout records the final verification pass for file router decomposition after R1-R5.

The closeout does not move additional runtime endpoints. It adds one global contract test that validates the complete `/api/v1/file` route map across all split file routers.

## 2. Final Router Map

| Slice | Router | Route Count | Scope |
| --- | --- | ---: | --- |
| R1 | `file_conversion_router.py` | 7 | Supported formats, conversion summary, conversion jobs, CAD processing |
| R2 | `file_viewer_router.py` | 13 | Viewer readiness, geometry assets, CAD artifacts, consumer summaries |
| R3 | `file_storage_router.py` | 3 | Upload, download, preview |
| R4 | `file_attachment_router.py` | 3 | Attach file, list item files, remove attachment |
| R4 | `file_metadata_router.py` | 1 | File metadata read |
| R5 | `file_router.py` | 0 | Unregistered compatibility shell |

Total owned `/api/v1/file` routes: 27.

`file_router.py` remains importable for compatibility, but it declares no route decorators and is not registered in `create_app()`.

## 3. Implementation

- Added `src/yuantus/meta_engine/tests/test_file_router_decomposition_closeout_contracts.py`.
- The closeout contract asserts:
  - Every `/api/v1/file` route has an explicit expected owner module.
  - Every `/api/v1/file` method/path pair is registered exactly once.
  - `file_router.py` has no `@file_router.*` decorators.
  - `app.py` registers split file routers in decomposition order.
  - `app.py` does not import or register legacy `file_router`.
- Added the closeout contract test to the CI contracts job.
- Registered this closeout document in `docs/DELIVERY_DOC_INDEX.md`.

## 4. Verification

Commands run locally before PR:

```bash
.venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_file_router_decomposition_closeout_contracts.py
```

Result: passed.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_file_conversion_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_attachment_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_metadata_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_router_shell_contracts.py
```

Result: `37 passed`.

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/api/tests/test_pact_provider_yuantus_plm.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_pact_provider_gate.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Result: `6 passed`.

```bash
git diff --check
```

Result: passed.

## 5. Review Checklist

- The closeout contract covers the full `/api/v1/file` route map.
- No runtime route behavior changes are introduced.
- Legacy `file_router.py` remains importable but unregistered.
- CI contracts job includes the closeout contract.
- Documentation index references this closeout report.

## 6. Closeout Status

Local pre-PR verification is complete. PR CI and post-merge verification are recorded in the final handoff after merge.
