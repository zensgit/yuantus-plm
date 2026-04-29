# Development Task - Phase 3 Tenant Import Rehearsal External Status

Date: 2026-04-29

## 1. Goal

Add a DB-free external status checker for P3.4.2 tenant import rehearsal.

The checker reads the operator execution packet and the artifacts that packet
expects to be produced by an external operator run. It reports the current
stage, the next action, and the next command without executing any command.

## 2. Rationale

After the operator packet exists, the remaining work is external:

- run row-copy rehearsal against non-production PostgreSQL DSNs;
- generate operator evidence;
- run the evidence gate;
- generate the archive manifest.

Those steps must happen in order. A small progress gate gives reviewers and
operators a deterministic way to see whether they should run row-copy, evidence
template, evidence gate, archive, or fix a malformed existing artifact.

## 3. Scope

- Add `src/yuantus/scripts/tenant_import_rehearsal_external_status.py`.
- Add `src/yuantus/tests/test_tenant_import_rehearsal_external_status.py`.
- Update `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- Update P3.4 TODO docs and `docs/DELIVERY_DOC_INDEX.md`.
- Add DEV/verification and TODO docs for the external status checker.

## 4. Non-Goals

- No database connections.
- No command execution.
- No row-copy rehearsal.
- No evidence acceptance.
- No archive creation.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 5. CLI Shape

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_external_status \
  --operator-packet-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --output-json output/tenant_<tenant-id>_external_status.json \
  --output-md output/tenant_<tenant-id>_external_status.md \
  --strict
```

## 6. Stage Contract

The checker can report:

- `awaiting_row_copy_rehearsal`
- `awaiting_operator_evidence_template`
- `awaiting_operator_evidence_markdown`
- `awaiting_evidence_gate`
- `awaiting_archive_manifest`
- `rehearsal_archive_ready`
- `blocked_external_status`

Missing future artifacts are not blockers. Existing malformed artifacts are
blockers.

## 7. Required Validations

- Operator packet schema is `p3.4.2-tenant-import-rehearsal-operator-packet-v1`.
- Operator packet has `ready_for_operator_execution=true`.
- Operator packet has `ready_for_cutover=false`.
- Operator packet has no blockers.
- Operator packet contains all expected commands.
- Existing row-copy, template, evidence, and archive JSON artifacts have the
  expected schema and ready fields.
- Existing JSON artifacts keep `ready_for_cutover=false`.
- Existing JSON artifacts have no blockers.
- Existing generated JSON artifacts have their companion Markdown outputs.

## 8. Output Contract

The JSON and Markdown reports must include:

- `current_stage`;
- `next_action`;
- `next_command_name`;
- `next_command`;
- `ready_for_external_progress`;
- `ready_for_cutover=false`;
- per-artifact existence and ready status;
- blockers.

## 9. Acceptance Criteria

- A green operator packet with no downstream outputs reports
  `awaiting_row_copy_rehearsal`.
- A complete accepted evidence/archive chain reports `rehearsal_archive_ready`.
- A malformed existing artifact reports `blocked_external_status`.
- `--strict` allows normal pending-next-action states.
- `--strict` returns non-zero for invalid existing artifacts.
- The tool never connects to a database and never authorizes cutover.
