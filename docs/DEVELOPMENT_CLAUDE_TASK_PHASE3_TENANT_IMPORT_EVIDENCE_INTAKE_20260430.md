# Development Task — Phase 3 Tenant Import Evidence Intake

Date: 2026-04-30

## 1. Objective

Add a DB-free evidence intake checklist for P3.4.2 tenant import rehearsal
artifacts.

The checklist runs after an operator has produced the row-copy, evidence, and
archive artifacts, but before reviewers consume the artifact set.

## 2. Scope

Implement one new script:

- `src/yuantus/scripts/tenant_import_rehearsal_evidence_intake.py`

The script reads the operator execution packet and validates the expected
outputs:

- `rehearsal_json`;
- `rehearsal_md`;
- `operator_evidence_template_json`;
- `operator_evidence_md`;
- `evidence_json`;
- `evidence_md`;
- `archive_json`;
- `archive_md`.

## 3. Required Checks

The script must:

- validate the operator packet schema and readiness fields;
- require every expected output path to exist;
- validate key JSON schema versions and ready fields;
- require `ready_for_cutover=false` on every JSON artifact;
- reject JSON or Markdown artifacts that are synthetic drill output;
- run the existing redaction guard against the full artifact set;
- keep its own `ready_for_cutover=false`.

## 4. Non-Goals

This task must not:

- open database connections;
- run row-copy;
- accept operator evidence;
- build archive manifests;
- run the evidence handoff gate;
- mark production cutover ready;
- enable runtime schema-per-tenant mode.

## 5. Output Files

- `src/yuantus/scripts/tenant_import_rehearsal_evidence_intake.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_stop_gate_contracts.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_EVIDENCE_INTAKE_20260430.md`
- `docs/PHASE3_TENANT_IMPORT_EVIDENCE_INTAKE_TODO_20260430.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EVIDENCE_INTAKE_20260430.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 6. Acceptance Criteria

- Green artifact set returns `ready_for_evidence_intake=true`.
- Missing artifacts block intake.
- Synthetic drill JSON and Markdown block intake.
- Plaintext PostgreSQL passwords block without leaking the secret.
- CLI strict mode exits 1 when blocked.
- Source contract confirms DB-free, intake-only scope.
- Full P3.4 focused suite remains green.

## 7. Stop Rule

If the checklist starts accepting synthetic drill output, calling the real
handoff gate, opening database connections, or setting `ready_for_cutover=true`,
stop and fix the scope before merge.
