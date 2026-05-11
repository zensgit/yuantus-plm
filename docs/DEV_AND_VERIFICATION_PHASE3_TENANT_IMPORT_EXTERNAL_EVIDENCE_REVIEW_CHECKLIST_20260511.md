# Dev & Verification - Phase 3 Tenant Import External Evidence Review Checklist

Date: 2026-05-11

## 1. Summary

Added a reviewer checklist for accepting real P3.4 external PostgreSQL
rehearsal evidence.

This is a documentation and contract slice. It does not run an operator
rehearsal, does not create or accept evidence, does not start Phase 5, and does
not authorize cutover.

## 2. Files Changed

- `docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_REVIEW_CHECKLIST_20260511.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_REVIEW_CHECKLIST_20260511.md`
- `src/yuantus/meta_engine/tests/test_p3_4_external_evidence_review_checklist_contracts.py`
- `.github/workflows/ci.yml`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The previous handoff packet tells the operator what to run. This checklist tells
the reviewer what to accept or reject after the operator produces real
artifacts.

The checklist deliberately separates three decisions:

1. Operator executes real non-production PostgreSQL rehearsal.
2. Reviewer accepts the evidence packet.
3. A later PR decides whether Phase 5 can start.

Only step 2 is covered here. `Ready for cutover: false` remains mandatory.

## 4. Contract Coverage

The new contract pins four invariants:

1. The checklist and this verification MD are indexed and the contract is wired
   into CI.
2. The checklist requires the complete reviewer-packet evidence chain.
3. The checklist rejects synthetic evidence, plaintext secrets, and any
   cutover-ready artifact.
4. The checklist states that evidence acceptance does not start Phase 5 or
   enable runtime schema-per-tenant mode.

The contract also checks the existing reviewer-packet source remains DB-free
and keeps `ready_for_cutover` false.

## 5. Non-Goals

- No runtime code changes.
- No script behavior changes.
- No database connection.
- No real DSN, password, or token in tracked files.
- No evidence creation or acceptance.
- No Phase 5 implementation.
- No production cutover.

## 6. Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_review_checklist_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_contracts_ci_yml_test_list_order.py \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_review_checklist_contracts.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_review_checklist_contracts.py \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_handoff_packet_contracts.py \
  src/yuantus/meta_engine/tests/test_next_cycle_post_p6_plan_gate_contracts.py \
  src/yuantus/tests/test_tenant_import_rehearsal_reviewer_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m py_compile \
  src/yuantus/meta_engine/tests/test_p3_4_external_evidence_review_checklist_contracts.py

git diff --check
```

## 7. Verification Results

- New review-checklist contract: 5 passed.
- CI list-order + new review-checklist contract: 6 passed.
- Focused suite (review checklist + handoff packet + post-P6 gate +
  reviewer-packet behavior + P3 stop-gate + doc-index trio): 36 passed.
- `py_compile` on the new contract: passed.
- `git diff --check`: clean.

## 8. Reviewer Checklist

- Confirm no runtime, migration, script, or CAD files changed.
- Confirm no real DSN or secret appears in tracked files.
- Confirm evidence acceptance remains separate from Phase 5 start.
- Confirm `Ready for cutover: false` is mandatory.
- Confirm the delivery-doc index entries are alphabetically sorted.
