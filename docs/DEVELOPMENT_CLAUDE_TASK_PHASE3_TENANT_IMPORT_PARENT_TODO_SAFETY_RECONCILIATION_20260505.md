# Development Task — Phase 3 Tenant Import Parent TODO Safety Reconciliation

Date: 2026-05-05

## 1. Goal

Reconcile the parent P3.4 tenant-import TODO and readiness status with the
DB-free operator-safety work completed on 2026-05-05.

This task is a documentation and contract closeout only. It must not mark the
real operator-run PostgreSQL rehearsal evidence as complete.

## 2. Background

Recent P3.4 local-safety PRs added:

- repo-external env-file template generation;
- DB-free env-file static precheck;
- env-file support in operator command-pack and full-closeout wrappers;
- generated operator command-file validation;
- command-file and env-file source safety hardening;
- wrapper-level unsafe env-file source guard contracts;
- runbook operator safety contracts.

The readiness status already described the safety hardening at a high level,
but the parent TODO and readiness checklist needed explicit line-item tracking
so future reviewers do not re-open completed DB-free safety work.

## 3. Scope

Modify only:

- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`;
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md`;
- `docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md`;
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`;
- delivery documentation for this closeout.

## 4. Non-Goals

Do not:

- add operator-run PostgreSQL rehearsal evidence;
- mark P3.4 rehearsal complete;
- enable production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`;
- import data into any production database;
- add local tooling that simulates real evidence;
- change runtime application code.

## 5. Required Contract Behavior

The stop-gate contract must assert all of the following:

- the 2026-05-05 DB-free safety closeouts are tracked as completed;
- the readiness status lists the current safe operator path;
- the real operator-run PostgreSQL rehearsal evidence item remains unchecked;
- the readiness status still points to external operator execution;
- `ready_for_cutover=false` remains the required state.

## 6. Implementation Notes

Keep the change narrow. This PR is a state-reconciliation PR, not another
operator tooling PR. Any shell input hardening discovered during review should
be split into a follow-up PR.

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

git diff --check
```
