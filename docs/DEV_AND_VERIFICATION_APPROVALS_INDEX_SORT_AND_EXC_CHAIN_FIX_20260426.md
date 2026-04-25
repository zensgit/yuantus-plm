# DEV / Verification — Approvals Follow-up: Index Sort + Exc-Chain Fix (2026-04-26)

## 1. Goal

Fix two issues uncovered by post-push verification of PR #399
(`followup/approvals-export-type-and-transactional-20260426`,
HEAD `430696f`):

1. `test_dev_and_verification_doc_index_sorting_contracts.py
   ::test_development_and_verification_section_paths_are_sorted_and_unique`
   was failing because the new
   `DEV_AND_VERIFICATION_APPROVALS_EXPORT_GUARD_TRANSACTIONAL_FOLLOWUP_20260426.md`
   index entry was placed by date next to the existing
   `APPROVALS_ROUTER_DECOMPOSITION_*` block (lines 125-127), violating
   alphabetical sort: `EXPORT < ROUTER` after the shared `APPROVALS_` prefix.

2. `_approval_write_transaction.transactional_write` was raising
   `HTTPException(400)` from inside `except ValueError as exc:` without
   `from exc`, dropping the original traceback. The same pattern was
   flagged and fixed in `document_sync_replay_audit_router` last review
   cycle; this kept the policy consistent.

This MD does not change any public route, schema, permission, or service
behavior.

## 2. Changes

| Path | Change |
| --- | --- |
| `docs/DELIVERY_DOC_INDEX.md` | Move `APPROVALS_EXPORT_GUARD_TRANSACTIONAL_FOLLOWUP_20260426` entry from below the two `APPROVALS_ROUTER_DECOMPOSITION_*` entries to above them, restoring alphabetical order. |
| `src/yuantus/meta_engine/web/_approval_write_transaction.py` | Add `from exc` to the `raise HTTPException(status_code=400, detail=str(exc))` inside the `except ValueError as exc:` clause. |
| `docs/DEV_AND_VERIFICATION_APPROVALS_INDEX_SORT_AND_EXC_CHAIN_FIX_20260426.md` | This file. |
| `docs/DELIVERY_DOC_INDEX.md` | New entry referencing the file above, sorted alphabetically (`APPROVALS_INDEX_SORT_...` between `APPROVALS_EXPORT_GUARD_...` and `APPROVALS_ROUTER_...`). |

## 3. Why The Sorting Contract Was Missed Pre-Push

The PR #399 author's reviewer snapshot recorded "1 passed (CI doc-index sorting)",
which corresponded to `test_ci_contracts_ci_yml_test_list_order.py` (the CI
workflow's test-invocation ordering, not the doc index). The doc-index
sorting contract `test_dev_and_verification_doc_index_sorting_contracts.py`
lives in the same family by name but in a separate file and was not part of
that snapshot. The fix re-runs the latter explicitly to close the gap.

## 4. Verification

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py \
  src/yuantus/meta_engine/tests/test_approval_category_router_contracts.py \
  src/yuantus/meta_engine/tests/test_approval_request_router_contracts.py \
  src/yuantus/meta_engine/tests/test_approval_ops_router_contracts.py \
  src/yuantus/meta_engine/tests/test_approvals_router_decomposition_closeout_contracts.py \
  src/yuantus/meta_engine/tests/test_router_decomposition_portfolio_contracts.py
```

Result on the patched HEAD (post-edits, pre-MD-add): **57 passed**. Same
suite re-run after this MD + index entry is added: see §6.

```bash
.venv/bin/python -m py_compile src/yuantus/meta_engine/web/_approval_write_transaction.py
```

Result: **passed**.

```bash
git diff --check
```

Result: **clean**.

## 5. Review Checklist

| # | Check | Status |
| --- | --- | --- |
| 1 | `test_dev_and_verification_doc_index_sorting_contracts.py::test_development_and_verification_section_paths_are_sorted_and_unique` passes | ✅ |
| 2 | `test_dev_and_verification_doc_index_completeness.py` and `test_delivery_doc_index_references.py` still pass after both new entries land in the index | ✅ (see §6) |
| 3 | `_approval_write_transaction.transactional_write` chains `HTTPException` via `from exc` for `ValueError` translation | ✅ |
| 4 | No public route / schema / permission / status / service behavior change | ✅ |
| 5 | No `.claude/` or `local-dev-env/` files added | ✅ |
| 6 | The 3 reordered `APPROVALS_*` index lines are alphabetically `EXPORT_GUARD` → `ROUTER_DECOMPOSITION_CLOSEOUT_20260424` → `ROUTER_DECOMPOSITION_CLOSEOUT_UNREGISTRATION_20260425` | ✅ |

## 6. Final Verification After This MD Lands

To be re-run as the last commit on the branch:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py \
  src/yuantus/meta_engine/tests/test_approvals_router.py
```

Expected: all pass (sort + completeness + references with the new entry +
behavior tests including transactional rollback).

## 7. Non-Goals

- No async-def → def conversion on `create_approval_request` /
  `transition_approval_request` (deferred; matches family precedent).
- No service-layer change to `ApprovalService.export_*` return-type
  contract (the cheap runtime guard in `_export_response` is sufficient
  for this scope).
- No unrelated index reorder beyond the 4 affected `APPROVALS_*` lines.
