# Development Task — Phase 3 Tenant Import Evidence Closeout Shell Entrypoint

Date: 2026-04-30

## 1. Goal

Add a repo-local shell entrypoint that runs the DB-free P3.4 evidence closeout
chain after real operator-run PostgreSQL rehearsal evidence has already been
produced and accepted.

This reduces the post-evidence handoff from five Python commands to one stable
`scripts/` command.

## 2. Scope

Implement:

- `scripts/run_tenant_import_evidence_closeout.sh`;
- focused shell-entrypoint tests;
- shell syntax/index contract wiring;
- runbook §20 shortcut;
- TODO and verification docs;
- delivery-doc and delivery-scripts index entries.

## 3. Non-Goals

Do not:

- run row-copy rehearsal;
- open database connections;
- create or edit operator evidence;
- accept synthetic drill output as real evidence;
- change evidence archive/intake/handoff/reviewer Python modules;
- authorize production cutover;
- enable runtime `TENANCY_MODE=schema-per-tenant`.

## 4. Design

The wrapper chains existing DB-free modules:

```text
evidence_json
  -> evidence_archive
  -> redaction_guard
  -> evidence_handoff
  -> evidence_intake
  -> reviewer_packet
```

The redaction guard input set is derived from the archive manifest artifact
list, so the handoff gate continues to prove every archived artifact was
scanned.

## 5. Output Defaults

Given:

```text
--artifact-prefix output/tenant_acme
```

the wrapper defaults to:

```text
output/tenant_acme_import_rehearsal_evidence_archive.json
output/tenant_acme_import_rehearsal_evidence_archive.md
output/tenant_acme_redaction_guard.json
output/tenant_acme_redaction_guard.md
output/tenant_acme_evidence_handoff.json
output/tenant_acme_evidence_handoff.md
output/tenant_acme_evidence_intake.json
output/tenant_acme_evidence_intake.md
output/tenant_acme_reviewer_packet.json
output/tenant_acme_reviewer_packet.md
```

## 6. Safety Contract

The wrapper runs only after real evidence exists. It must not generate that
evidence or mark cutover ready.

Every downstream artifact remains `ready_for_cutover=false`.

## 7. Verification

Run:

```bash
.venv/bin/python -m pytest -q \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_closeout_shell_entrypoint.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_archive.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_handoff.py \
  src/yuantus/tests/test_tenant_import_rehearsal_evidence_intake.py \
  src/yuantus/tests/test_tenant_import_rehearsal_reviewer_packet.py

.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py \
  src/yuantus/meta_engine/tests/test_delivery_scripts_index_entries_contracts.py

git diff --check
```
