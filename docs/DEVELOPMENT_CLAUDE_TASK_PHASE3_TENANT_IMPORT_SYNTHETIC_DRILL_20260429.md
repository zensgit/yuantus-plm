# Development Task — Phase 3 Tenant Import Synthetic Drill

Date: 2026-04-29

## 1. Objective

Add a DB-free synthetic drill for the P3.4.2 tenant import rehearsal toolchain.

The drill gives operators a safe way to practice the local artifact and
redaction commands before real non-production PostgreSQL rehearsal evidence is
available.

## 2. Scope

Implement one new local script:

- `src/yuantus/scripts/tenant_import_rehearsal_synthetic_drill.py`

The script must:

- generate clearly synthetic local artifacts;
- run the existing redaction guard against those artifacts;
- write JSON and Markdown drill reports;
- keep `ready_for_cutover=false`;
- keep `real_rehearsal_evidence=false`;
- never build a real archive or evidence handoff report.

## 3. Non-Goals

This task must not:

- open source or target database connections;
- run tenant row-copy rehearsal;
- accept operator-run PostgreSQL evidence;
- build a real rehearsal archive manifest;
- pass the real evidence handoff gate;
- enable `TENANCY_MODE=schema-per-tenant`;
- change migrations, Alembic envs, runtime routers, settings, or database code.

## 4. Output Files

- `src/yuantus/scripts/tenant_import_rehearsal_synthetic_drill.py`
- `src/yuantus/tests/test_tenant_import_rehearsal_synthetic_drill.py`
- `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`
- `docs/PHASE3_TENANT_IMPORT_REHEARSAL_TODO_20260427.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_20260429.md`
- `docs/PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_TODO_20260429.md`
- `docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_SYNTHETIC_DRILL_20260429.md`
- `docs/DELIVERY_DOC_INDEX.md`

## 5. Required Report Shape

The drill report must include:

- `schema_version=p3.4.2-tenant-import-rehearsal-synthetic-drill-v1`;
- `synthetic_drill=true`;
- `real_rehearsal_evidence=false`;
- `db_connection_attempted=false`;
- `ready_for_synthetic_drill=true` only when the redaction scan is clean;
- `ready_for_operator_evidence=false`;
- `ready_for_evidence_handoff=false`;
- `ready_for_cutover=false`.

## 6. Generated Synthetic Artifacts

The script should generate three synthetic artifacts under `--artifact-dir`:

- synthetic operator evidence Markdown;
- synthetic external status JSON;
- synthetic operator notes Markdown.

Every generated artifact must be visibly synthetic and must not claim to be a
real rehearsal result.

## 7. Redaction Integration

The script must call the existing redaction guard directly and write:

- `<artifact-prefix>_redaction_guard.json`;
- `<artifact-prefix>_redaction_guard.md`.

It must not call the real archive or evidence handoff gate.

## 8. Failure Mode

The script should support a test-only plaintext-secret injection flag so the
redaction failure path can be tested without external fixtures.

When the injected artifact contains a plaintext PostgreSQL password:

- `ready_for_synthetic_drill=false`;
- strict CLI mode exits 1;
- the report must not leak the plaintext secret.

## 9. Tests

Add tests for:

- clean drill writes artifacts and redaction report;
- generated artifacts are marked synthetic and not real evidence;
- plaintext-secret injection blocks without leaking the secret;
- Markdown states the non-evidence boundary;
- CLI writes JSON and Markdown in strict mode;
- CLI strict mode exits 1 on redaction failure;
- source contract blocks DB/runtime/archive/handoff scope creep.

## 10. Runbook

Add a runbook section after the evidence handoff gate:

- command example;
- expected flags;
- explicit warning that the output is not real operator evidence;
- instruction to keep the real operator-run PostgreSQL evidence TODO unchecked.

## 11. Acceptance Criteria

- New tests pass.
- Existing redaction, evidence handoff, archive, external status, and operator
  request tests still pass.
- Full P3.4 focused suite stays green.
- Runbook and doc-index contracts pass.
- `py_compile` passes for the new script.
- `git diff --check` is clean.

## 12. Stop Rule

Stop and ask for real operator input instead of adding more local bypasses if a
change would make synthetic output satisfy the real evidence or cutover gates.
