# Claude Task — Phase 3 Tenant Import Rehearsal Handoff

Date: 2026-04-28

## 1. Goal

Add a safe handoff generator that answers one operational question:

```text
Can Claude start implementing P3.4.2 tenant import rehearsal now?
```

The answer must be derived from the machine-readable readiness report, not
from chat state or reviewer memory.

## 2. Scope

- Add `yuantus.scripts.tenant_import_rehearsal_handoff`.
- Consume a P3.4.2 readiness JSON report.
- Emit JSON and Markdown handoff reports.
- Set `ready_for_claude=true` only when readiness is fully green.
- Include the exact implementation scope and non-goals for Claude.
- Keep plaintext DSN secrets out of generated reports.

## 3. Non-Goals

- No importer implementation.
- No database connections.
- No source or target writes.
- No schema creation, migration, rollback, or cleanup.
- No production cutover.
- No runtime `TENANCY_MODE=schema-per-tenant` enablement.

## 4. CLI

```bash
PYTHONPATH=src python -m yuantus.scripts.tenant_import_rehearsal_handoff \
  --readiness-json output/tenant_<tenant-id>_import_rehearsal_readiness.json \
  --output-json output/tenant_<tenant-id>_claude_import_rehearsal_handoff.json \
  --output-md output/tenant_<tenant-id>_claude_import_rehearsal_task.md \
  --strict
```

## 5. Acceptance

`ready_for_claude=true` only when:

- readiness schema is `p3.4.2-import-rehearsal-readiness-v1`;
- dry-run schema is `p3.4.1-dry-run-v1`;
- readiness `ready_for_import=true`;
- readiness `ready_for_rehearsal=true`;
- readiness blockers are empty;
- tenant id, target schema, redacted target URL, and dry-run JSON are present.

If any condition fails, the command writes a blocked handoff report and returns
1 in `--strict` mode.

## 6. Generated Handoff Contents

The Markdown handoff tells Claude:

- whether it can start;
- which tenant/schema/readiness/dry-run artifacts are in scope;
- what to implement in `yuantus.scripts.tenant_import_rehearsal`;
- required safety order: `--confirm-rehearsal` and readiness validation before
  any DB connection;
- required non-goals, including no runtime cutover and no global table import;
- required verification commands for the actual importer PR.

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_readiness.py \
  src/yuantus/tests/test_tenant_migration_dry_run.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py

.venv/bin/python -m py_compile \
  src/yuantus/scripts/tenant_import_rehearsal_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_handoff.py

git diff --check
```
