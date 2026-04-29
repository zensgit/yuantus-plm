# Development Task - Phase 3 Tenant Import Rehearsal Evidence Template

Date: 2026-04-29

## 1. Goal

Add a small operator-facing template generator for P3.4.2 rehearsal evidence.

The generator reads the green row-copy rehearsal report and renders a Markdown
file with the exact `## Rehearsal Evidence Sign-Off` block consumed by
`tenant_import_rehearsal_evidence`.

## 2. Rationale

After #438, the evidence gate is strict. Hand-written operator evidence can fail
on field names, missing values, or unredacted database URLs. This task removes
that formatting risk without weakening the evidence gate.

## 3. Scope

- Add `src/yuantus/scripts/tenant_import_rehearsal_evidence_template.py`.
- Add `src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py`.
- Update `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- Update P3.4 TODO docs and `docs/DELIVERY_DOC_INDEX.md`.
- Add DEV/verification and TODO docs for the template generator.

## 4. Non-Goals

- No database connections.
- No row-copy execution.
- No evidence acceptance by itself.
- No schema creation, migration, downgrade, cleanup, or rollback.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 5. CLI Shape

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_evidence_template \
  --rehearsal-json output/tenant_<tenant-id>_import_rehearsal.json \
  --backup-restore-owner "<owner>" \
  --rehearsal-window "<window>" \
  --rehearsal-executed-by "<operator>" \
  --rehearsal-result pass \
  --evidence-reviewer "<reviewer>" \
  --date "<yyyy-mm-dd>" \
  --output-json output/tenant_<tenant-id>_operator_rehearsal_evidence_template.json \
  --output-md output/tenant_<tenant-id>_operator_rehearsal_evidence.md \
  --strict
```

## 6. Required Validations

- Input rehearsal report schema is `p3.4.2-tenant-import-rehearsal-v1`.
- Rehearsal report has `ready_for_rehearsal_import=true`.
- Rehearsal report has `import_executed=true`.
- Rehearsal report has `db_connection_attempted=true`.
- Rehearsal report has `ready_for_cutover=false`.
- Rehearsal report has no blockers.
- Tenant ID, target schema, and redacted target URL are present.
- Operator fields are present under `--strict`.
- `Rehearsal result` is an accepted pass value.

## 7. Output Contract

The output Markdown must include:

- title `Tenant Import Rehearsal Operator Evidence`;
- template schema marker;
- redacted target context from the rehearsal report;
- `## Rehearsal Evidence Sign-Off`;
- the exact field names consumed by the evidence gate;
- `Ready for cutover: false`.

The JSON sidecar must include blockers and
`ready_for_operator_evidence_template`.

## 8. Test Plan

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_template.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence.py \
  src/yuantus/tests/test_tenant_import_rehearsal.py \
  src/yuantus/tests/test_tenant_import_rehearsal_implementation_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_next_action.py \
  src/yuantus/tests/test_tenant_import_rehearsal_source_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_target_preflight.py \
  src/yuantus/tests/test_tenant_import_rehearsal_plan.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

Also run py_compile and `git diff --check`.

## 9. Acceptance Criteria

- The generated Markdown is parseable by `tenant_import_rehearsal_evidence`.
- The tool never prints or writes unredacted database passwords.
- Incomplete operator fields fail under `--strict`.
- Blocked rehearsal reports cannot produce ready evidence templates.
- All focused and doc-index tests pass.
