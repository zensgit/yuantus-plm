# Dev & Verification - Next-Cycle Post Exception-Chaining Status Refresh

Date: 2026-05-14

## 1. Summary

Added a small post-closeout planning guard after direct residual router
exception-chaining work landed on `main=99a9fd7`.

The stronger AST guard also found two f-string-style file-router fallback
mappings that the prior direct `detail=str(e)` scan did not catch. This PR
chains those misses, records the local router exception-chaining debt as
closed, and keeps the existing operating gate intact: Phase 5 remains blocked
until accepted real P3.4 external PostgreSQL rehearsal evidence is recorded.

## 2. Files Changed

- `docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md`
- `src/yuantus/meta_engine/web/file_storage_router.py`
- `src/yuantus/meta_engine/web/file_viewer_router.py`
- `src/yuantus/meta_engine/tests/test_next_cycle_post_exception_chaining_status_contracts.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`
- `docs/DEV_AND_VERIFICATION_NEXT_CYCLE_POST_EXCEPTION_CHAINING_STATUS_REFRESH_20260514.md`

## 3. Design

The new contract pins four invariants:

1. The next-cycle plan has a 2026-05-14 status refresh that records the direct
   closeout landing point `main=99a9fd7`.
2. The plan marks the broader router exception-chaining debt as closed without
   weakening the Phase 5 external-evidence gate.
3. `src/yuantus/meta_engine/web` and `src/yuantus/api` have no bare
   stringified `HTTPException` mappings without exception chaining.
4. The residual closeout contract, this new contract, and this verification MD
   remain CI-wired and indexed.

The scanner is AST-based, not only regex-based. It catches direct
`detail=str(e)`, `detail=repr(exc)`, `detail=repr(err.args)`, f-string-style
`detail=f"{exc}"`, and attribute-style `fastapi.HTTPException(...)` patterns
when they are raised without a `from e` / `from exc` cause.

## 4. Claude Code Assist

Claude Code was used read-only through the local `claude` CLI. It did not edit
files. The read-only recommendation matched the implemented scope: keep the
slice docs/contracts only, avoid runtime changes, and preserve the Phase 5
external-evidence gate.

## 5. Behavior

Two runtime lines changed, both preserving response status and detail while
adding `HTTPException.__cause__`:

- `file_storage_router.py`: download fallback failure still returns
  `500 Download failed: <original exception>`.
- `file_viewer_router.py`: generic file-viewer download fallback failure still
  returns `500 <prefix> download failed: <original exception>`.

## 6. Non-Goals

- No Phase 5 implementation.
- No P3.4 evidence synthesis or cutover enablement.
- No database, migration, tenant provisioning, scheduler, CAD plugin, or
  external-service behavior change.

## 7. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  src/yuantus/meta_engine/web/file_storage_router.py \
  src/yuantus/meta_engine/web/file_viewer_router.py \
  src/yuantus/meta_engine/tests/test_next_cycle_post_exception_chaining_status_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_next_cycle_post_exception_chaining_status_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_next_cycle_post_exception_chaining_status_contracts.py \
  src/yuantus/meta_engine/tests/test_residual_router_exception_chaining_closeout.py \
  src/yuantus/meta_engine/tests/test_next_cycle_post_p6_plan_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_file_router_exception_chaining_closeout.py \
  src/yuantus/meta_engine/tests/test_file_storage_router_contracts.py \
  src/yuantus/meta_engine/tests/test_file_viewer_router_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -c \
  "from yuantus.api.app import create_app; app = create_app(); print(f'routes={len(app.routes)} middleware={len(app.user_middleware)}')"

git diff --check
```

## 8. Verification Results

- `py_compile` on the two touched routers and new/touched contracts: passed.
- New post-exception-chaining status contract: `4 passed`.
- Focused aggregate suite:
  - post-exception-chaining status contract
  - residual router exception-chaining closeout contract
  - post-P6 plan-gate contract
  - doc-index trio
  - CI list-order contract
  - Result: `24 passed`.
- Adjacent file-router regression:
  - file exception-chaining closeout
  - file storage router contracts
  - file viewer router contracts
  - Result: `19 passed`.
- Boot check: `routes=676 middleware=4`.
- `git diff --check`: clean.
- Claude Code read-only staged-diff review: highest-value scanner-width
  feedback applied before commit.

## 9. Review Checklist

- Confirm this PR only changes two runtime lines, docs, contracts, and CI
  wiring.
- Confirm the plan records `main=99a9fd7` as the direct residual closeout
  landing point, not as permission to start Phase 5.
- Confirm Phase 5 remains blocked by accepted real P3.4 external PostgreSQL
  rehearsal evidence.
- Confirm the AST scanner does not ban chained `HTTPException(... detail=str(e))
  from e` patterns.
- Confirm the delivery-doc index entry is alphabetically sorted.

This file is indexed as
`docs/DEV_AND_VERIFICATION_NEXT_CYCLE_POST_EXCEPTION_CHAINING_STATUS_REFRESH_20260514.md`.
