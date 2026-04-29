# Dev & Verification — Phase 3 Tenant Import Operator Request

Date: 2026-04-29

## 1. Summary

Added a DB-free P3.4.2 operator request packet that converts a green/pending
external-status report into an operator-facing JSON/Markdown handoff.

The new packet makes the next external action explicit while keeping production
cutover blocked.

## 2. Files Changed

- `src/yuantus/scripts/tenant_import_rehearsal_operator_request.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_OPERATOR_REQUEST_20260429.md`
- `docs/PHASE3_TENANT_IMPORT_OPERATOR_REQUEST_TODO_20260429.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_OPERATOR_REQUEST_20260429.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 3. Design

The operator request tool intentionally reads only one input:

```text
external_status_json
```

It validates that the upstream external status is structurally green:

- expected schema version;
- `ready_for_external_progress=true`;
- `ready_for_cutover=false`;
- no blockers;
- supported current stage;
- next command present unless the archive is already ready.

The output report contains:

- current stage;
- next action;
- next command name;
- next command;
- required operator inputs for the stage;
- artifact summary;
- `ready_for_operator_request`;
- `ready_for_cutover=false`.

## 4. Stage Mapping

| Stage | Required operator input |
| --- | --- |
| `awaiting_row_copy_rehearsal` | Source and target DB env vars plus non-production confirmation. |
| `awaiting_operator_evidence_template` | Owner, window, operator, reviewer, date. |
| `awaiting_operator_evidence_markdown` | Completed evidence Markdown. |
| `awaiting_evidence_gate` | Reviewed evidence Markdown. |
| `awaiting_archive_manifest` | Accepted evidence gate JSON. |
| `rehearsal_archive_ready` | Archive review and cutover hold. |

Blocked status is not convertible to an operator request. The upstream artifact
must be fixed first.

## 5. Safety Boundaries

This PR does not:

- open database connections;
- run row-copy;
- accept or generate real operator evidence;
- build real archive manifests;
- authorize production cutover;
- import production data;
- enable `TENANCY_MODE=schema-per-tenant`.

The source-level contract test also asserts that the new script does not import
runtime tenancy mode, SQLAlchemy engines, or sessions.

## 6. Verification Commands

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py \
  src/yuantus/tests/test_tenant_import_rehearsal_external_status.py \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_packet.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_runbook_index_completeness.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py \
  src/yuantus/meta_engine/tests/test_readme_runbooks_sorting_contracts.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_operator_request.py

git diff --check
```

## 7. Verification Results

- Operator request + adjacent P3.4 + doc-index focused suite:
  `27 passed in 0.24s`.
- Full P3.4 focused suite + doc-index trio:
  `144 passed, 1 skipped, 1 warning in 1.20s`.
- Runbook/index contracts: `5 passed in 0.03s`.
- `py_compile`: passed.
- `git diff --check`: clean.

## 8. Remaining External Work

The next real transition still requires external operator execution:

- run row-copy rehearsal against non-production PostgreSQL;
- generate real operator evidence;
- run evidence gate against real operator evidence;
- build archive manifest;
- keep production cutover blocked until separately authorized.
