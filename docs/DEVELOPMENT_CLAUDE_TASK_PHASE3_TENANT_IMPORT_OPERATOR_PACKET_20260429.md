# Development Task - Phase 3 Tenant Import Operator Packet

Date: 2026-04-29

## 1. Goal

Add a DB-free operator execution packet generator for P3.4.2 tenant import
rehearsal.

The packet converts a green implementation packet into the exact operator
command sequence for:

- row-copy rehearsal;
- operator evidence template;
- evidence gate;
- archive manifest.

## 2. Rationale

The P3.4 toolchain can now build a row-copy rehearsal, validate operator
evidence, and archive accepted evidence. The remaining external work is an
operator-run non-production PostgreSQL rehearsal.

Operators need one reviewable packet that lists commands, output paths, and
environment-variable placeholders without exposing DSNs or executing any
database work.

## 3. Scope

- Add `src/yuantus/scripts/tenant_import_rehearsal_operator_packet.py`.
- Add `src/yuantus/tests/test_tenant_import_rehearsal_operator_packet.py`.
- Update `docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md`.
- Update P3.4 TODO docs and `docs/DELIVERY_DOC_INDEX.md`.
- Add DEV/verification and TODO docs for the operator packet.

## 4. Non-Goals

- No database connections.
- No row-copy execution.
- No evidence acceptance.
- No archive creation against real operator evidence.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.
- No credential capture in JSON or Markdown.

## 5. CLI Shape

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_operator_packet \
  --implementation-packet-json output/tenant_<tenant-id>_importer_implementation_packet.json \
  --artifact-prefix output/tenant_<tenant-id> \
  --output-json output/tenant_<tenant-id>_operator_execution_packet.json \
  --output-md output/tenant_<tenant-id>_operator_execution_packet.md \
  --strict
```

The default DSN placeholders are `${SOURCE_DATABASE_URL}` and
`${TARGET_DATABASE_URL}`. Custom placeholders are allowed only as uppercase
shell environment variable names.

## 6. Required Validations

- Implementation packet schema is `p3.4.2-importer-implementation-packet-v1`.
- Implementation packet has `ready_for_claude_importer=true`.
- Implementation packet has `ready_for_cutover=false`.
- Implementation packet has no blockers.
- Required implementation packet fields are present.
- Fresh implementation-packet validation still passes against the referenced
  next-action JSON.
- Fresh validation paths match the stored implementation packet paths.
- Source and target DSN placeholder names are uppercase shell environment
  variable names.

## 7. Output Contract

The JSON and Markdown reports must include:

- `ready_for_operator_execution`;
- `ready_for_cutover=false`;
- tenant ID, target schema, and redacted target URL;
- implementation packet path;
- artifact prefix;
- source and target DSN environment-variable names;
- four ordered commands;
- expected output artifact paths;
- blockers.

## 8. Command Order

The generated command order is fixed:

1. `tenant_import_rehearsal`
2. `tenant_import_rehearsal_evidence_template`
3. `tenant_import_rehearsal_evidence`
4. `tenant_import_rehearsal_evidence_archive`

The operator packet does not execute these commands. It only makes the handoff
auditable before an operator runs the non-production rehearsal.

## 9. Test Plan

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_operator_packet.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
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

Also run runbook/index contracts, py_compile, and `git diff --check`.

## 10. Acceptance Criteria

- Green implementation packet produces `ready_for_operator_execution=true`.
- Stale upstream artifact blocks operator execution.
- Invalid environment-variable names block operator execution.
- CLI writes JSON and Markdown reports.
- `--strict` returns non-zero when blocked.
- The generated commands use environment-variable placeholders, not DSN values.
- The tool never connects to a database.
- `ready_for_cutover` remains false.
