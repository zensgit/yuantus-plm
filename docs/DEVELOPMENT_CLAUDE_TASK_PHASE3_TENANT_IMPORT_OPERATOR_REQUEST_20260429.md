# Development Task — Phase 3 Tenant Import Operator Request

Date: 2026-04-29

## 1. Goal

Add a DB-free operator request packet for P3.4.2 tenant import rehearsal.

The request packet converts a green or pending external-status report into a
single operator-facing JSON/Markdown artifact with:

- current stage;
- required operator inputs;
- exact next command;
- artifact summary;
- `ready_for_cutover=false`.

## 2. Context

The P3.4 toolchain already has:

- implementation packet;
- guarded row-copy rehearsal;
- operator evidence template;
- evidence gate;
- archive manifest;
- operator execution packet;
- external status checker.

The external status checker is accurate but still requires an operator to read
status JSON/Markdown and infer what inputs are required for the next action.
This task adds a narrow handoff layer that makes the next external action
explicit without running it.

## 3. Scope

Add:

- `src/yuantus/scripts/tenant_import_rehearsal_operator_request.py`;
- `src/yuantus/tests/test_tenant_import_rehearsal_operator_request.py`;
- this task document;
- a TODO document;
- a DEV_AND_VERIFICATION document;
- runbook instructions;
- delivery doc index entries.

## 4. Non-Goals

- No database connection.
- No row-copy execution.
- No operator evidence creation or acceptance.
- No archive creation.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No secrets in tracked docs.

## 5. CLI Contract

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_request \
  --external-status-json output/tenant_<tenant-id>_external_status.json \
  --output-json output/tenant_<tenant-id>_operator_request.json \
  --output-md output/tenant_<tenant-id>_operator_request.md \
  --strict
```

Strict mode exits 0 only when:

- external status has the expected schema version;
- external status has `ready_for_external_progress=true`;
- external status has `ready_for_cutover=false`;
- external status has no blockers;
- current stage is supported;
- a next command exists for all non-archive-ready stages.

## 6. Supported Stages

| External status stage | Operator request action |
| --- | --- |
| `awaiting_row_copy_rehearsal` | Provide source/target env vars and run row-copy command. |
| `awaiting_operator_evidence_template` | Provide owner/window/operator/reviewer/date and run template command. |
| `awaiting_operator_evidence_markdown` | Complete or regenerate operator evidence Markdown. |
| `awaiting_evidence_gate` | Review operator evidence and run evidence gate. |
| `awaiting_archive_manifest` | Build archive manifest from accepted evidence. |
| `rehearsal_archive_ready` | Review archive and hold cutover gate. |

Blocked external status is intentionally not a supported stage. It must be
fixed upstream rather than converted into an operator request.

## 7. Output Contract

The JSON report includes:

- `schema_version`;
- `external_status_json`;
- tenant/schema/redacted target URL;
- `current_stage`;
- `next_action`;
- `next_command_name`;
- `next_command`;
- `required_operator_inputs`;
- `artifacts`;
- `ready_for_operator_request`;
- `ready_for_cutover=false`;
- `blockers`.

The Markdown report renders the same information for operator handoff.

## 8. Acceptance Criteria

- Green/pending external status produces `ready_for_operator_request=true`.
- Blocked external status produces blockers and strict exit 1.
- Archive-ready status produces a review request with no next command and
  still keeps `ready_for_cutover=false`.
- The script does not import runtime settings, SQLAlchemy engines, sessions, or
  any runtime cutover path.
- Runbook and delivery index are updated.

## 9. Verification

Run:

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

## 10. Stop Rule

If any test requires real DB credentials, stop. This task must remain DB-free.
